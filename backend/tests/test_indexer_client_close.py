"""The indexer (AsyncElasticsearch) clients opened by the scheduled alert job are closed.

Every AsyncElasticsearch owns an aiohttp session with its own TLS connections. The auto alert job used to
open 2-3 clients per alert and never close them, so the garbage collector closed the sockets and asyncio
logged ``SSL shutdown timed out`` ~1,500 times per run.

Run with: cd backend && python -m pytest tests/test_indexer_client_close.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from contextlib import asynccontextmanager  # noqa: E402

from app.connectors.wazuh_indexer.utils import universal  # noqa: E402
from app.incidents.routes import incident_alert as route  # noqa: E402
from app.incidents.schema.alert_collection import AlertPayloadItem  # noqa: E402
from app.incidents.schema.incident_alert import CreateAlertRequest  # noqa: E402
from app.incidents.services import alert_collection  # noqa: E402
from app.incidents.services import incident_alert as service  # noqa: E402


class FakeAsyncElasticsearch:
    """Counts constructions and close() calls across the whole test."""

    created = 0
    closed = 0

    def __init__(self, *args, **kwargs):
        type(self).created += 1
        self.updates = []

    async def close(self):
        type(self).closed += 1

    async def get(self, index, id):
        return {"_id": id, "_index": index, "_version": 1, "_source": {"timestamp": "2026-01-01T00:00:00", "syslog_type": "wazuh"}}

    async def update(self, index, id, body):
        self.updates.append((index, id))

    async def search(self, **kwargs):
        return {"hits": {"hits": [], "total": {"value": 0}}}


@pytest.fixture(autouse=True)
def fake_indexer():
    FakeAsyncElasticsearch.created = 0
    FakeAsyncElasticsearch.closed = 0

    @asynccontextmanager
    async def fake_db_session():
        yield None

    async def fake_connector_info(name, session):
        return {"connector_url": "https://indexer.invalid:9200", "connector_username": "u", "connector_password": "p"}

    with patch.object(universal, "AsyncElasticsearch", FakeAsyncElasticsearch), patch.object(
        universal, "get_db_session", fake_db_session
    ), patch.object(universal, "get_connector_info_from_db", fake_connector_info):
        yield


def _alert(n):
    return AlertPayloadItem(
        **{
            "_index": "gl-events_0",
            "_id": f"gl-{n}",
            "_source": {
                "id": f"gl-{n}",
                "event_definition_type": "t",
                "event_definition_id": "e",
                "origin_context": f"urn:graylog:message:es:wazuh_0:doc-{n}",
                "timestamp": "2026-01-01T00:00:00",
                "timestamp_processing": "2026-01-01T00:00:00",
                "streams": [],
                "source_streams": [],
                "message": "m",
                "source": "s",
                "key_tuple": [],
                "key": "k",
                "priority": 1,
                "alert": True,
                "fields": {},
            },
        },
    )


# --------------------------------------------------------------------------------------
# context manager
# --------------------------------------------------------------------------------------


def test_context_manager_closes_client_on_success():
    async def go():
        async with universal.wazuh_indexer_client_async() as client:
            assert isinstance(client, FakeAsyncElasticsearch)
            assert FakeAsyncElasticsearch.closed == 0

    asyncio.run(go())
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (1, 1)


def test_context_manager_closes_client_and_propagates_when_body_raises():
    async def go():
        async with universal.wazuh_indexer_client_async():
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(go())
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (1, 1)


def test_context_manager_leaves_a_borrowed_client_open():
    async def go():
        borrowed = FakeAsyncElasticsearch()
        async with universal.wazuh_indexer_client_async(client=borrowed) as client:
            assert client is borrowed
        return borrowed

    asyncio.run(go())
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (1, 0)


# --------------------------------------------------------------------------------------
# service functions without a client open and close their own
# --------------------------------------------------------------------------------------


def test_get_single_alert_details_without_client_closes_its_own_even_on_failure():
    async def go():
        ok = await service.get_single_alert_details(CreateAlertRequest(index_name="wazuh_0", alert_id="a1"))
        assert ok.syslog_type == "wazuh"

    asyncio.run(go())
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (1, 1)

    async def failing():
        async def broken_get(self, index, id):
            raise ConnectionError("down")

        with patch.object(FakeAsyncElasticsearch, "get", broken_get):
            await service.get_single_alert_details(CreateAlertRequest(index_name="wazuh_0", alert_id="a1"))

    with pytest.raises(Exception):
        asyncio.run(failing())
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (2, 2)


def test_add_alert_to_document_and_add_copilot_alert_id_close_their_own_client():
    asyncio.run(service.add_alert_to_document(CreateAlertRequest(index_name="wazuh_0", alert_id="a1"), 7))
    asyncio.run(alert_collection.add_copilot_alert_id(CreateAlertRequest(index_name="gl-events_0", alert_id="g1"), 7))
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (2, 2)


def test_get_alerts_not_created_without_client_closes_its_own():
    async def indices():
        return ["gl-events_0"]

    with patch.object(alert_collection, "return_graylog_events_index_names", indices):
        payload, remaining = asyncio.run(alert_collection.get_alerts_not_created_in_copilot())
    assert payload.alerts == [] and remaining == 0
    assert (FakeAsyncElasticsearch.created, FakeAsyncElasticsearch.closed) == (1, 1)


def test_create_alert_passes_the_shared_client_to_every_indexer_call():
    seen = {}

    class Source(dict):
        def to_dict(self):
            return dict(self)

    async def fake_details(alert_details, es_client=None):
        seen["details"] = es_client
        return SimpleNamespace(syslog_type="wazuh", source=Source(), index="i", id="d")

    async def noop(*args, **kwargs):
        return None

    async def fake_full(payload, customer_code, session, es_client=None, **kwargs):
        seen["full"] = es_client
        return 11

    marker = object()
    payload = SimpleNamespace(index_name="i", index_id="d", alert_title_payload="t", timefield_payload="x", ioc_payload=None)

    async def build(*args, **kwargs):
        return payload

    with patch.object(service, "get_single_alert_details", fake_details), patch.object(
        service, "validate_syslog_type_source", noop
    ), patch.object(service, "get_customer_code", noop), patch.object(service, "is_customer_code_valid", noop), patch.object(
        service, "build_alert_payload", build
    ), patch.object(
        service, "open_alert_exists", noop
    ), patch.object(
        service, "create_alert_full", fake_full
    ):
        result = asyncio.run(service.create_alert(CreateAlertRequest(index_name="wazuh_0", alert_id="a1"), None, es_client=marker))
    assert result == 11
    assert seen == {"details": marker, "full": marker}
    assert FakeAsyncElasticsearch.created == 0


# --------------------------------------------------------------------------------------
# the scheduled job: one client for the whole run
# --------------------------------------------------------------------------------------


def _patch_job(batches):
    """Serve ``batches`` (lists of alerts) one per call; the real service functions run against the fake client."""
    calls = {"n": 0}

    async def indices():
        return ["gl-events_0"]

    async def fake_fetch(es_client, index, query, batch_size=100):
        i = calls["n"]
        calls["n"] += 1
        batch = batches[i]
        if isinstance(batch, Exception):
            raise batch
        return batch, 0

    async def fake_create_alert(request, session, es_client=None):
        # Same indexer calls the real create_alert makes, using the shared client.
        await service.get_single_alert_details(request, es_client=es_client)
        await service.add_alert_to_document(request, 5, es_client=es_client)
        return 5

    return (
        patch.object(alert_collection, "return_graylog_events_index_names", indices),
        patch.object(alert_collection, "fetch_alerts_batch", fake_fetch),
        patch.object(route, "create_alert", fake_create_alert),
    )


def _run_job(batches):
    p1, p2, p3 = _patch_job(batches)
    with p1, p2, p3:
        return asyncio.run(route.create_alert_auto_route(session=None))


def test_auto_job_with_many_alerts_opens_one_client_and_closes_it_once():
    n = 150  # two batches: 100 + 50
    alerts = [_alert(i) for i in range(n)]
    response = _run_job([alerts[:100], alerts[100:]])
    assert response.alerts_created == n and response.alerts_failed == 0
    assert FakeAsyncElasticsearch.created == 1
    assert FakeAsyncElasticsearch.closed == 1


def test_auto_job_closes_the_client_when_a_later_batch_raises():
    with pytest.raises(RuntimeError, match="indexer went away"):
        _run_job([[_alert(i) for i in range(100)], RuntimeError("indexer went away")])
    assert FakeAsyncElasticsearch.created == 1
    assert FakeAsyncElasticsearch.closed == 1
