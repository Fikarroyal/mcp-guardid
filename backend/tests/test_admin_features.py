import httpx
import pytest

from main import app
from tests.conftest import ROLE_EMAILS, TEST_PASSWORD


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client, role: str) -> dict:
    r = await client.post("/api/v1/auth/login", json={"email": ROLE_EMAILS[role], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ------------------------------------------------------------ registration --
async def test_register_forces_viewer_role(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "new.user@mcpguardid.id", "full_name": "New User", "password": "secret123",
        "role_name": "Enterprise Administrator",  # must be ignored
    })
    assert r.status_code == 201
    assert r.json()["role"] == "Viewer"


async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@mcpguardid.id", "full_name": "Dupe", "password": "secret123"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409


# ---------------------------------------------------------------- accounts --
async def test_accounts_crud_and_authorization(client):
    admin = await _login(client, "Enterprise Administrator")
    support = await _login(client, "IT Support")
    body = {"email": "crud.user@mcpguardid.id", "full_name": "Crud", "password": "secret123", "role_name": "IT Support"}

    assert (await client.post("/api/v1/users", json=body, headers=support)).status_code == 403
    created = await client.post("/api/v1/users", json=body, headers=admin)
    assert created.status_code == 201
    uid = created.json()["id"]

    assert (await client.get("/api/v1/users", headers=support)).status_code == 200  # directory readable
    upd = await client.put(f"/api/v1/users/{uid}", json={"role_name": "Network Engineer", "is_active": False}, headers=admin)
    assert upd.json()["role_name"] == "Network Engineer" and upd.json()["is_active"] is False
    assert (await client.put(f"/api/v1/users/{uid}", json={"role_name": "Nope"}, headers=admin)).status_code == 422
    assert (await client.delete(f"/api/v1/users/{uid}", headers=support)).status_code == 403
    assert (await client.delete(f"/api/v1/users/{uid}", headers=admin)).status_code == 200


async def test_cannot_delete_or_deactivate_self(client):
    admin = await _login(client, "Enterprise Administrator")
    me = (await client.get("/api/v1/auth/me", headers=admin)).json()
    assert (await client.delete(f"/api/v1/users/{me['id']}", headers=admin)).status_code == 400
    assert (await client.put(f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=admin)).status_code == 400


# ---------------------------------------------------------------- api keys --
async def test_api_key_lifecycle_and_real_authentication(client):
    admin = await _login(client, "Enterprise Administrator")
    created = await client.post("/api/v1/api-keys", json={"name": "ci-bot", "role_name": "Viewer"}, headers=admin)
    assert created.status_code == 201
    raw, key_id = created.json()["raw_key"], created.json()["id"]
    assert raw.startswith("gid_")

    # The key genuinely authenticates, and acts with ONLY its bound role.
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert me.status_code == 200 and me.json()["role_name"] == "Viewer"
    denied = await client.post("/api/v1/users", headers={"Authorization": f"Bearer {raw}"},
                                json={"email": "x@mcpguardid.id", "full_name": "x", "password": "secret123", "role_name": "Viewer"})
    assert denied.status_code == 403

    listing = (await client.get("/api/v1/api-keys", headers=admin)).json()
    assert all("raw_key" not in k for k in listing)  # raw key never listed again

    assert (await client.post(f"/api/v1/api-keys/{key_id}/revoke", headers=admin)).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})).status_code == 401
    assert (await client.delete(f"/api/v1/api-keys/{key_id}", headers=admin)).status_code == 200


async def test_api_key_privilege_ceiling_and_role_gate(client):
    infra = await _login(client, "Infrastructure Administrator")
    support = await _login(client, "IT Support")
    body = {"name": "escalate", "role_name": "Enterprise Administrator"}
    assert (await client.post("/api/v1/api-keys", json=body, headers=infra)).status_code == 403
    assert (await client.post("/api/v1/api-keys", json={"name": "n", "role_name": "Viewer"}, headers=support)).status_code == 403


# ---------------------------------------------------- roles & permissions --
async def test_role_ceiling_edit_changes_policy_decisions(client):
    admin = await _login(client, "Enterprise Administrator")
    dba = await _login(client, "Database Administrator")
    roles = {r["name"]: r for r in (await client.get("/api/v1/roles", headers=admin)).json()}
    dba_role = roles["Database Administrator"]

    before = await client.post("/api/v1/agent/query", json={"query": "Restart database production sekarang."}, headers=dba)
    assert before.json()["permission_result"] == "APPROVAL_REQUIRED"

    assert (await client.put(f"/api/v1/roles/{dba_role['id']}", json={"max_risk_level": "LOW"}, headers=admin)).status_code == 200
    after = await client.post("/api/v1/agent/query", json={"query": "Restart database production sekarang."}, headers=dba)
    assert after.json()["permission_result"] == "DENIED"  # the edit is genuinely enforced

    await client.put(f"/api/v1/roles/{dba_role['id']}", json={"max_risk_level": "HIGH"}, headers=admin)  # restore


async def test_category_block_is_enforced_and_gated(client):
    admin = await _login(client, "Enterprise Administrator")
    support = await _login(client, "IT Support")
    assert (await client.put("/api/v1/roles/permissions/set", params={"role_name": "IT Support", "category": "network", "allowed": False},
                              headers=support)).status_code == 403

    ok = await client.put("/api/v1/roles/permissions/set", params={"role_name": "IT Support", "category": "network", "allowed": False},
                           headers=admin)
    assert ok.status_code == 200
    tools = {t["name"]: t for t in (await client.get("/api/v1/tools", headers=support)).json()}
    r = await client.post(f"/api/v1/tools/{tools['ping_device']['id']}/execute", json={"input_data": {"target": "x"}}, headers=support)
    assert r.status_code == 403

    await client.put("/api/v1/roles/permissions/set", params={"role_name": "IT Support", "category": "network", "allowed": True},
                      headers=admin)  # restore
    r2 = await client.post(f"/api/v1/tools/{tools['ping_device']['id']}/execute", json={"input_data": {"target": "x"}}, headers=support)
    assert r2.status_code == 200


async def test_cannot_lock_own_role(client):
    admin = await _login(client, "Enterprise Administrator")
    r = await client.put("/api/v1/roles/permissions/set",
                          params={"role_name": "Enterprise Administrator", "category": "server", "allowed": False}, headers=admin)
    assert r.status_code == 400


# ------------------------------------------------------------ execution log --
async def test_execution_log_filter_and_purge(client):
    admin = await _login(client, "Enterprise Administrator")
    support = await _login(client, "IT Support")
    tools = {t["name"]: t for t in (await client.get("/api/v1/tools", headers=admin)).json()}
    await client.post(f"/api/v1/tools/{tools['check_dns']['id']}/execute", json={"input_data": {"hostname": "a.test"}}, headers=admin)

    rows = (await client.get("/api/v1/executions", params={"tool": "check_dns"}, headers=support)).json()
    assert rows and all(r["tool_name"] == "check_dns" for r in rows)
    assert (await client.post("/api/v1/executions/purge", params={"older_than_days": 30}, headers=support)).status_code == 403
    purge = await client.post("/api/v1/executions/purge", params={"older_than_days": 30}, headers=admin)
    assert purge.status_code == 200 and purge.json()["deleted"] == 0  # nothing that old
    assert (await client.delete(f"/api/v1/executions/{rows[0]['id']}", headers=admin)).status_code == 200


# ------------------------------------------------------------ tool registry --
async def test_tool_registry_crud(client):
    admin = await _login(client, "Enterprise Administrator")
    support = await _login(client, "IT Support")
    body = {"name": "check_queue_depth", "description": "Measure message queue depth for a broker.",
            "category": "server", "risk_level": "HIGH", "requires_approval": False, "required_roles": ["System Administrator"]}

    assert (await client.post("/api/v1/tools", json=body, headers=support)).status_code == 403
    created = await client.post("/api/v1/tools", json=body, headers=admin)
    assert created.status_code == 201
    assert created.json()["requires_approval"] is True  # HIGH forces approval regardless of the request
    tid = created.json()["id"]
    assert (await client.post("/api/v1/tools", json=body, headers=admin)).status_code == 409
    assert (await client.post("/api/v1/tools", json={**body, "name": "bad", "risk_level": "EXTREME"}, headers=admin)).status_code == 422

    upd = await client.put(f"/api/v1/tools/{tid}", json={"enabled": False, "risk_level": "LOW"}, headers=admin)
    assert upd.json()["enabled"] is False and upd.json()["risk_level"] == "LOW"
    assert (await client.delete(f"/api/v1/tools/{tid}", headers=support)).status_code == 403
    assert (await client.delete(f"/api/v1/tools/{tid}", headers=admin)).status_code == 200
    assert (await client.get(f"/api/v1/tools/{tid}", headers=admin)).status_code == 404
