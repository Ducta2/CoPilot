"""Three endpoints that returned HTTP 500 on staging now answer sensibly.

1. ``GET /incidents/alerts/alerts/not-created``: the service returns ``(AlertsPayload, int)`` since
   the batch rework but the route declared ``AlertsPayload``, so FastAPI's response validation
   failed on every call. The route unpacks the tuple.
2. ``GET /graylog/metrics``: ``["data"]["gauges"]`` was read unguarded, so any Graylog answer that was
   not the metrics document (403, ApiError JSON) became ``KeyError`` -> 500. It is now a 502 with
   a user-safe message, and the detail goes to the log.
3. ``/nuclei/*``: the web assessment module is called without error handling, so an absent
   container (``ConnectError``) surfaced as 500. Network failures and 5xx -> 503, bad JSON -> 502.

Run with: cd backend && python -m pytest tests/test_endpoint_500_fixes.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.graylog.services import monitoring  # noqa: E402
from app.incidents.schema.alert_collection import AlertsPayload  # noqa: E402
from app.incidents.services import alert_collection  # noqa: E402
from app.integrations.nuclei.services import nuclei as nuclei_service  # noqa: E402
from app.routers import incidents as incidents_router_module  # noqa: E402

# --------------------------------------------------------------------------------------
# 1. alerts/not-created
# --------------------------------------------------------------------------------------

ANA = {"Authorization": "Bearer ana"}


def _alerts_request(service_result):
    async def _inner():
        app = FastAPI()
        app.include_router(incidents_router_module.router)

        async def fake_service(*args, **kwargs):
            return service_result

        async def resolve_user(self, request, username):
            return SimpleNamespace(id=2, username="ana", role_id=2)

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, ["analyst"])), patch.object(
            AuthHandler, "_resolve_user", resolve_user
        ), patch("app.incidents.routes.incident_alert.get_alerts_not_created_in_copilot", fake_service):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/incidents/alerts/alerts/not-created", headers=ANA)

    return asyncio.run(_inner())


def test_alerts_not_created_route_unpacks_the_service_tuple():
    response = _alerts_request((AlertsPayload(alerts=[]), 0))

    assert response.status_code == 200
    body = response.json()
    assert body["alerts"] == []
    assert body["success"] is True


def test_alerts_not_created_service_still_returns_payload_and_remaining():
    # The other caller (/create/auto) depends on the tuple contract; the route fix must not change it.
    assert alert_collection.get_alerts_not_created_in_copilot.__annotations__["return"] == alert_collection.Tuple[AlertsPayload, int]


# --------------------------------------------------------------------------------------
# 2. graylog metrics
# --------------------------------------------------------------------------------------

JOURNAL_OK = {"success": True, "data": {"uncommitted_journal_entries": 7}}


def _async(value):
    async def fetch():
        return value

    return fetch


def _metrics(monkeypatch, metrics_payload, journal_payload=JOURNAL_OK):
    monkeypatch.setattr(monitoring, "fetch_metrics_from_graylog", _async(metrics_payload))
    monkeypatch.setattr(monitoring, "fetch_uncommitted_journal_entries", _async(journal_payload))
    return asyncio.run(monitoring.get_metrics())


@pytest.mark.parametrize(
    "payload",
    [
        {"success": True, "data": {"type": "ApiError", "message": "forbidden"}},
        {"success": True, "data": {"gauges": {}}},
        {"success": True, "data": None},
        {"success": True},
    ],
)
def test_metrics_payload_without_gauges_is_a_502(monkeypatch, payload):
    with pytest.raises(HTTPException) as exc:
        _metrics(monkeypatch, payload)

    assert exc.value.status_code == 502
    assert exc.value.detail == "Không lấy được số liệu từ dịch vụ thu thập log"


def test_metrics_unsuccessful_fetch_is_a_502(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        _metrics(monkeypatch, {"success": False, "data": {}})

    assert exc.value.status_code == 502


def test_metrics_502_does_not_leak_upstream_body(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        _metrics(monkeypatch, {"success": True, "data": {"type": "ApiError", "message": "secret-token-abc"}})

    assert "secret-token-abc" not in exc.value.detail


def test_metrics_complete_payload_is_unchanged(monkeypatch):
    payload = {"success": True, "data": {"gauges": {}, "counters": {}}}

    response = _metrics(monkeypatch, payload)

    assert response.success is True
    assert response.uncommitted_journal_entries == 7


# --------------------------------------------------------------------------------------
# 3. nuclei
# --------------------------------------------------------------------------------------


def _patch_http(monkeypatch, method, result):
    async def fake(self, *args, **kwargs):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(httpx.AsyncClient, method, fake)


def _response(status, json=None, method="GET"):
    return httpx.Response(status, json=json, request=httpx.Request(method, "http://copilot-nuclei-module/x"))


CALLS = [
    ("get", lambda: nuclei_service.get_nuclei_reports_available()),
    ("get", lambda: nuclei_service.get_nuclei_report("example.com")),
    ("delete", lambda: nuclei_service.delete_nuclei_report("example.com")),
    ("post", lambda: nuclei_service.post_to_copilot_nuclei_module(nuclei_service.NucleiScanRequest(host="example.com"))),
]


@pytest.mark.parametrize("method,call", CALLS)
@pytest.mark.parametrize("error", [httpx.ConnectError("boom"), httpx.ConnectTimeout("slow"), httpx.ReadTimeout("slow")])
def test_nuclei_network_errors_are_a_503(monkeypatch, method, call, error):
    _patch_http(monkeypatch, method, error)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(call())

    assert exc.value.status_code == 503
    assert exc.value.detail == "Dịch vụ đánh giá web chưa sẵn sàng"


@pytest.mark.parametrize("method,call", CALLS)
def test_nuclei_5xx_is_a_503(monkeypatch, method, call):
    _patch_http(monkeypatch, method, _response(502, {"detail": "internal"}))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(call())

    assert exc.value.status_code == 503
    assert "internal" not in exc.value.detail


@pytest.mark.parametrize("method,call", CALLS)
def test_nuclei_schema_mismatch_is_a_502(monkeypatch, method, call):
    _patch_http(monkeypatch, method, _response(200, {"unexpected": True}))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(call())

    assert exc.value.status_code == 502


def test_nuclei_invalid_json_is_a_502(monkeypatch):
    _patch_http(monkeypatch, "get", httpx.Response(200, content=b"<html>", request=httpx.Request("GET", "http://x")))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(nuclei_service.get_nuclei_reports_available())

    assert exc.value.status_code == 502


@pytest.mark.parametrize(
    "method,call,detail",
    [
        ("get", lambda: nuclei_service.get_nuclei_reports_available(), "Không tìm thấy báo cáo đánh giá web"),
        ("get", lambda: nuclei_service.get_nuclei_report("example.com"), "Không tìm thấy báo cáo đánh giá web này"),
        ("delete", lambda: nuclei_service.delete_nuclei_report("example.com"), "Không tìm thấy báo cáo đánh giá web này"),
    ],
)
def test_nuclei_404_stays_a_404_without_the_platform_name(monkeypatch, method, call, detail):
    _patch_http(monkeypatch, method, _response(404, {"detail": "nope"}, method.upper()))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(call())

    assert exc.value.status_code == 404
    assert exc.value.detail == detail
    assert "nuclei" not in exc.value.detail.lower()


def test_nuclei_success_paths_are_unchanged(monkeypatch):
    _patch_http(monkeypatch, "get", _response(200, {"reports": ["a"], "success": True, "message": "ok"}))
    assert asyncio.run(nuclei_service.get_nuclei_reports_available()).reports == ["a"]

    _patch_http(monkeypatch, "get", _response(200, {"markdown": "# r", "success": True, "message": "ok"}))
    assert asyncio.run(nuclei_service.get_nuclei_report("example.com")).markdown == "# r"

    _patch_http(monkeypatch, "delete", _response(200, {"success": True, "message": "ok"}))
    assert asyncio.run(nuclei_service.delete_nuclei_report("example.com")).success is True

    _patch_http(monkeypatch, "post", _response(200, {"success": True, "message": "ok"}))
    scan = asyncio.run(nuclei_service.post_to_copilot_nuclei_module(nuclei_service.NucleiScanRequest(host="example.com")))
    assert scan.success is True
