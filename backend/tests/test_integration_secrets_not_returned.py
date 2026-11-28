"""Integration, network connector and customer meta responses must not carry stored secrets.

**The trap this file exists for:** ``GET /integrations/customer_integrations`` (and the
``/{customer_code}`` variant) returned every ``auth_value`` in clear (API keys, client
secrets, AWS secret keys). ``GET /network_connectors/customer_network_connectors`` did the
same, and ``GET /customers/{code}/meta`` returned the Wazuh registration password. All of
them are open to analysts, not just admins.

The fix mirrors ``tests/test_connector_secrets_not_returned.py``: the public response
schemas drop the secret and report an ``*_set`` flag; the internal schemas keep it, because
provisioning code reads ``auth_value`` from ``get_customer_integrations_by_customer_code``.
A secret left blank on update keeps the stored value.

Route tests run the real routers over in-memory SQLite (only the tables needed).

Run with: cd backend && python -m pytest tests/test_integration_secrets_not_returned.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import FastAPI  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.db.universal_models  # noqa: E402,F401
from app.auth.utils import AuthHandler  # noqa: E402
from app.customers.schema.customers import CustomerMetaOut  # noqa: E402
from app.customers.schema.customers import CustomerMetaResponse  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import CustomersMeta  # noqa: E402
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    AvailableIntegrations,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    AvailableIntegrationsAuthKeys,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    CustomerIntegrations,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationAuthKeys,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationService,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationSubscription,
)
from app.middleware.customer_access import verify_customer_code_access  # noqa: E402
from app.network_connectors.models.network_connectors import (  # noqa: E402
    AvailableNetworkConnectors,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    AvailableNetworkConnectorsKeys,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    CustomerNetworkConnectors,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    NetworkConnectorsKeys,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    NetworkConnectorsService,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    NetworkConnectorsSubscription,
)
from app.routers import customers as customers_router_module  # noqa: E402
from app.routers import integrations as integrations_router_module  # noqa: E402
from app.routers import network_connectors as network_connectors_router_module  # noqa: E402

CC = "ACME"
INTEGRATION_SECRET = "int-secret-value-123"
NETWORK_SECRET = "net-secret-value-456"
WAZUH_PASSWORD = "wazuh-reg-password-789"
NEW_SECRET = "brand-new-secret-000"

_TABLES = [
    "customers",
    "customersmeta",
    "available_integrations",
    "available_integrations_auth_keys",
    "customer_integrations",
    "integration_services",
    "integration_subscriptions",
    "integration_auth_keys",
    "available_network_connectors",
    "available_network_connectors_keys",
    "customer_network_connectors",
    "network_connectors_services",
    "network_connectors_subscriptions",
    "network_connectors_keys",
]


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        tables = [SQLModel.metadata.tables[t] for t in _TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        async with self.factory() as s:
            s.add(Customers(customer_code=CC, customer_name="Acme", customer_email="a@example.invalid", customer_type="x"))
            s.add(
                CustomersMeta(
                    customer_code=CC,
                    customer_name="Acme",
                    customer_meta_graylog_index="idx",
                    customer_meta_graylog_stream="stream",
                    customer_meta_grafana_org_id="org",
                    customer_meta_wazuh_group="grp",
                    customer_meta_wazuh_auth_password=WAZUH_PASSWORD,
                ),
            )
            # Integration "Mimecast" with one secret key
            s.add(AvailableIntegrations(id=1, integration_name="Mimecast", description="d", integration_details="x"))
            s.add(AvailableIntegrationsAuthKeys(integration_id=1, integration_name="Mimecast", auth_key_name="API_KEY"))
            s.add(IntegrationService(id=1, service_name="Mimecast", auth_type="api"))
            s.add(
                CustomerIntegrations(
                    id=1, customer_code=CC, customer_name="Acme", integration_service_id=1, integration_service_name="Mimecast"
                )
            )
            s.add(IntegrationSubscription(id=1, customer_id=1, integration_service_id=1))
            s.add(IntegrationAuthKeys(id=1, subscription_id=1, auth_key_name="API_KEY", auth_value=INTEGRATION_SECRET))
            # Network connector "Fortinet" with one secret key
            s.add(AvailableNetworkConnectors(id=1, network_connector_name="Fortinet", description="d", network_connector_details="x"))
            s.add(AvailableNetworkConnectorsKeys(network_connector_id=1, network_connector_name="Fortinet", auth_key_name="API_KEY"))
            s.add(NetworkConnectorsService(id=1, service_name="Fortinet", auth_type="api"))
            s.add(
                CustomerNetworkConnectors(
                    id=1,
                    customer_code=CC,
                    customer_name="Acme",
                    network_connector_service_id=1,
                    network_connector_service_name="Fortinet",
                ),
            )
            s.add(NetworkConnectorsSubscription(id=1, customer_id=1, network_connectors_service_id=1))
            s.add(NetworkConnectorsKeys(id=1, subscription_id=1, auth_key_name="API_KEY", auth_value=NETWORK_SECRET))
            await s.commit()
        return self

    async def stored(self, model, **where):
        async with self.factory() as s:
            row = (await s.execute(select(model).filter_by(**where))).scalars().first()
            return row


def _app(db: Db) -> FastAPI:
    app = FastAPI()
    app.include_router(integrations_router_module.router)
    app.include_router(network_connectors_router_module.router)
    app.include_router(customers_router_module.router)

    async def _session():
        async with db.factory() as s:
            yield s

    app.dependency_overrides[get_db] = _session
    app.dependency_overrides[verify_customer_code_access] = lambda: CC
    return app


USERS = {"admin": SimpleNamespace(id=1, username="admin", role_id=1), "ana": SimpleNamespace(id=2, username="ana", role_id=2)}
SCOPES = {"admin": ["admin"], "ana": ["analyst"]}
ANA = {"Authorization": "Bearer ana"}
ADMIN = {"Authorization": "Bearer admin"}


def _run(scenario):
    async def _inner():
        db = await Db().create()
        transport = httpx.ASGITransport(app=_app(db))

        async def resolve_user(self, request, username):
            return USERS.get(username)

        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                try:
                    return await scenario(client, db)
                finally:
                    await db.engine.dispose()

    return asyncio.run(_inner())


# --------------------------------------------------------------------------------------
# Integrations
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/integrations/customer_integrations", f"/integrations/customer_integrations/{CC}"])
def test_customer_integrations_get_never_returns_auth_value(path):
    async def scenario(client, db):
        return await client.get(path, headers=ANA)

    resp = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert INTEGRATION_SECRET not in resp.text
    key = resp.json()["available_integrations"][0]["integration_subscriptions"][0]["integration_auth_keys"][0]
    assert "auth_value" not in key
    assert key["auth_value_set"] is True
    assert key["auth_key_name"] == "API_KEY"


def test_customer_integrations_flag_false_when_value_empty():
    async def scenario(client, db):
        async with db.factory() as s:
            row = (await s.execute(select(IntegrationAuthKeys))).scalars().first()
            row.auth_value = ""
            await s.commit()
        return await client.get("/integrations/customer_integrations", headers=ANA)

    key = _run(scenario).json()["available_integrations"][0]["integration_subscriptions"][0]["integration_auth_keys"][0]
    assert key["auth_value_set"] is False


def test_provisioning_still_reads_the_secret_from_the_internal_response():
    """``get_customer_integrations_by_customer_code`` is called directly by provisioning code."""
    from app.integrations.routes import get_customer_integrations_by_customer_code

    async def scenario(client, db):
        async with db.factory() as s:
            return await get_customer_integrations_by_customer_code(CC, s)

    internal = _run(scenario)
    assert internal.available_integrations[0].integration_subscriptions[0].integration_auth_keys[0].auth_value == INTEGRATION_SECRET


def _update_integration(client, value):
    return client.put(
        f"/integrations/update_integration/{CC}",
        headers=ANA,
        json={"integration_name": "Mimecast", "integration_auth_keys": [{"auth_key_name": "API_KEY", "auth_value": value}]},
    )


@pytest.mark.parametrize("blank", ["", "   "])
def test_integration_update_with_blank_secret_keeps_stored_value(blank):
    async def scenario(client, db):
        resp = await _update_integration(client, blank)
        return resp, (await db.stored(IntegrationAuthKeys, id=1)).auth_value

    resp, stored = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert stored == INTEGRATION_SECRET


def test_integration_update_with_new_secret_replaces_it():
    async def scenario(client, db):
        resp = await _update_integration(client, NEW_SECRET)
        return resp, (await db.stored(IntegrationAuthKeys, id=1)).auth_value

    resp, stored = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert stored == NEW_SECRET
    assert NEW_SECRET not in resp.text


# --------------------------------------------------------------------------------------
# Network connectors
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", ["/network_connectors/customer_network_connectors", f"/network_connectors/customer_network_connectors/{CC}"]
)
def test_customer_network_connectors_get_never_returns_auth_value(path):
    async def scenario(client, db):
        return await client.get(path, headers=ANA)

    resp = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert NETWORK_SECRET not in resp.text
    key = resp.json()["available_network_connectors"][0]["network_connectors_subscriptions"][0]["network_connectors_keys"][0]
    assert "auth_value" not in key
    assert key["auth_value_set"] is True


def test_network_connector_update_internal_flow_still_sees_the_secret():
    from app.network_connectors.routes import (
        get_customer_network_connectors_by_customer_code,
    )

    async def scenario(client, db):
        async with db.factory() as s:
            return await get_customer_network_connectors_by_customer_code(CC, s)

    internal = _run(scenario)
    assert (
        internal.available_network_connectors[0].network_connectors_subscriptions[0].network_connectors_keys[0].auth_value == NETWORK_SECRET
    )


def _update_network(client, value):
    return client.put(
        f"/network_connectors/update_network_connector/{CC}",
        headers=ANA,
        json={"network_connector_name": "Fortinet", "network_connector_auth_keys": [{"auth_key_name": "API_KEY", "auth_value": value}]},
    )


def test_network_connector_update_with_blank_secret_keeps_stored_value():
    async def scenario(client, db):
        resp = await _update_network(client, "")
        return resp, (await db.stored(NetworkConnectorsKeys, id=1)).auth_value

    resp, stored = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert stored == NETWORK_SECRET


def test_network_connector_update_with_new_secret_replaces_it():
    async def scenario(client, db):
        resp = await _update_network(client, NEW_SECRET)
        return resp, (await db.stored(NetworkConnectorsKeys, id=1)).auth_value

    resp, stored = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert stored == NEW_SECRET


# --------------------------------------------------------------------------------------
# Customer meta
# --------------------------------------------------------------------------------------


def test_customer_meta_get_never_returns_wazuh_password():
    async def scenario(client, db):
        return await client.get(f"/customers/{CC}/meta", headers=ANA)

    resp = _run(scenario)
    assert resp.status_code == 200, resp.text
    assert WAZUH_PASSWORD not in resp.text
    meta = resp.json()["customer_meta"]
    assert "customer_meta_wazuh_auth_password" not in meta
    assert meta["customer_meta_wazuh_auth_password_set"] is True
    assert meta["customer_meta_wazuh_group"] == "grp"


def test_customer_meta_schema_flag_false_without_password():
    out = CustomerMetaOut(
        customer_meta_graylog_index="i",
        customer_meta_graylog_stream="s",
        customer_meta_grafana_org_id="o",
        customer_meta_wazuh_group="g",
        customer_meta_wazuh_auth_password=None,
    )
    dumped = CustomerMetaResponse(customer_meta=out, success=True, message="ok").model_dump(mode="json")
    assert dumped["customer_meta"]["customer_meta_wazuh_auth_password_set"] is False
    assert "customer_meta_wazuh_auth_password" not in dumped["customer_meta"]


def test_edr_install_still_reads_the_password_from_the_db_model():
    """The EDR installer reads ``CustomersMeta`` (the ORM row), never the response schema."""
    from app.customer_provisioning.services import edr_install

    async def scenario(client, db):
        async with db.factory() as s:
            return await edr_install._get_customer_meta(CC, s)

    assert _run(scenario).customer_meta_wazuh_auth_password == WAZUH_PASSWORD
