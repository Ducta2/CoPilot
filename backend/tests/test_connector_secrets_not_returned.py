"""Connector API responses must not carry stored secrets.

**The trap this file exists for:** ``GET /connectors`` used to serialise the ORM row
as-is, so every admin browser session received each connector's plaintext password
and API key. The response model now drops them and reports ``*_set`` flags instead;
``ConnectorResponse`` (the internal shape verification code reads) keeps them.

Schema-only tests: no network, no database.

Run with: cd backend && python -m pytest tests/test_connector_secrets_not_returned.py
"""

from datetime import datetime

from app.connectors.schema import ConnectorListResponse
from app.connectors.schema import ConnectorPublicResponse
from app.connectors.schema import ConnectorResponse
from app.connectors.schema import ConnectorsListResponse

_ROW = dict(
    id=1,
    connector_name="Example",
    connector_type="4.4.1",
    connector_url="https://example.invalid:9200",
    connector_last_updated=datetime(2026, 1, 1),
    connector_username="svc",
    connector_password="s3cret-value",
    connector_api_key="api-key-value",
    connector_configured=True,
    connector_verified=True,
    connector_enabled=True,
    connector_accepts_host_only=False,
    connector_accepts_api_key=True,
    connector_accepts_username_password=True,
    connector_accepts_file=False,
    connector_accepts_extra_data=False,
)


def test_public_response_drops_secrets_and_sets_flags():
    dumped = ConnectorPublicResponse(**_ROW).model_dump(mode="json")
    assert "connector_password" not in dumped
    assert "connector_api_key" not in dumped
    assert dumped["connector_password_set"] is True
    assert dumped["connector_api_key_set"] is True
    assert dumped["connector_username"] == "svc"


def test_flags_false_when_nothing_stored():
    row = {**_ROW, "connector_password": None, "connector_api_key": ""}
    dumped = ConnectorPublicResponse(**row).model_dump(mode="json")
    assert dumped["connector_password_set"] is False
    assert dumped["connector_api_key_set"] is False


def test_list_and_single_envelopes_never_serialise_secrets():
    internal = ConnectorResponse(**_ROW)
    many = ConnectorsListResponse(connectors=[internal.model_dump()], success=True, message="ok").model_dump_json()
    one = ConnectorListResponse(connector=internal.model_dump(), success=True, message="ok").model_dump_json()
    for body in (many, one):
        assert "s3cret-value" not in body
        assert "api-key-value" not in body


def test_internal_shape_still_carries_secrets():
    assert ConnectorResponse(**_ROW).connector_password == "s3cret-value"
