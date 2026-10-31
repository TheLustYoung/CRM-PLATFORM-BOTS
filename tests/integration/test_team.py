"""Admin team: accounts, roles and permissions."""
from backend.main import app
from backend.models import Admin, Audit
from backend.services import team
from backend.services.auth import hasher

PASSWORD = "test-password-only"


def sign_in(client, username, password=PASSWORD):
    client.cookies.clear()
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_existing_admins_are_owners_and_me_lists_permissions(admin_client):
    me = admin_client.get("/api/admin/me").json()
    assert me["role"] == "owner" and me["permissions"] == list(team.PERMISSIONS)


def test_create_account_and_role_limits_what_it_can_do(admin_client, db):
    made = admin_client.post("/api/admin/team/accounts", json={"username": "helper", "password": PASSWORD, "role": "support"})
    assert made.status_code == 200 and made.json()["role"] == "support"
    assert admin_client.post("/api/admin/team/accounts", json={"username": "Helper", "password": PASSWORD, "role": "support"}).json()["detail"] == "username_taken"
    assert admin_client.post("/api/admin/team/accounts", json={"username": "x y", "password": PASSWORD, "role": "support"}).json()["detail"] == "bad_username"
    assert admin_client.post("/api/admin/team/accounts", json={"username": "shorty", "password": "short", "role": "support"}).json()["detail"] == "short_password"

    assert sign_in(admin_client, "helper").status_code == 200
    me = admin_client.get("/api/admin/me").json()
    assert me["role"] == "support" and "settings.manage" not in me["permissions"]
    assert admin_client.get("/api/admin/users").status_code == 200
    assert admin_client.get("/api/admin/files").status_code == 200
    assert admin_client.get("/api/admin/overview").status_code == 200
    for method, path in [("GET", "/api/admin/settings"), ("GET", "/api/admin/payments"), ("GET", "/api/admin/team"),
                         ("PATCH", "/api/admin/bots/media"), ("GET", "/api/admin/audit"), ("GET", "/api/admin/broadcasts")]:
        assert admin_client.request(method, path, json={}).status_code == 403, path


def test_no_privilege_escalation(admin_client, db):
    role = admin_client.post("/api/admin/team/roles", json={"name": "Team lead", "permissions": ["users.view", "users.manage", "team.manage"]}).json()
    admin_client.post("/api/admin/team/accounts", json={"username": "lead", "password": PASSWORD, "role": role["id"]})
    owner_id = db.query(Admin).filter_by(username="operator").one().id
    sign_in(admin_client, "lead")
    assert admin_client.post("/api/admin/team/accounts", json={"username": "boss2", "password": PASSWORD, "role": "owner"}).json()["detail"] == "role_above_you"
    assert admin_client.patch(f"/api/admin/team/accounts/{owner_id}", json={"active": False}).json()["detail"] == "above_you"
    assert admin_client.post("/api/admin/team/roles", json={"name": "Money", "permissions": ["money.manage"]}).json()["detail"] == "role_above_you"
    ok = admin_client.post("/api/admin/team/accounts", json={"username": "junior", "password": PASSWORD, "role": role["id"]})
    assert ok.status_code == 200  # same rights as the lead: allowed
    lead_id = db.query(Admin).filter_by(username="lead").one().id
    assert admin_client.patch(f"/api/admin/team/accounts/{lead_id}", json={"role": "viewer"}).json()["detail"] == "not_yourself"


def test_changes_sign_people_out_and_last_owner_stays(admin_client, db):
    admin_client.post("/api/admin/team/accounts", json={"username": "temp", "password": PASSWORD, "role": "viewer"})
    temp = db.query(Admin).filter_by(username="temp").one()
    owner = db.query(Admin).filter_by(username="operator").one()
    sign_in(admin_client, "temp")
    assert admin_client.get("/api/admin/me").status_code == 200

    sign_in(admin_client, "operator")
    assert admin_client.patch(f"/api/admin/team/accounts/{owner.id}", json={"role": "viewer"}).json()["detail"] == "not_yourself"
    assert admin_client.patch(f"/api/admin/team/accounts/{temp.id}", json={"role": "support"}).status_code == 200
    temp_cookie_client_session = sign_in(admin_client, "temp")
    assert temp_cookie_client_session.status_code == 200
    db.refresh(temp)
    old_version = temp.session_version
    sign_in(admin_client, "operator")
    admin_client.patch(f"/api/admin/team/accounts/{temp.id}", json={"password": "another-long-pass"})
    db.refresh(temp)
    assert temp.session_version == old_version + 1
    assert sign_in(admin_client, "temp").status_code == 401  # old password no longer works
    assert sign_in(admin_client, "temp", "another-long-pass").status_code == 200


def test_old_session_stops_working_after_block(client, db):
    db.add(Admin(username="first", password_hash=hasher.hash(PASSWORD)))
    db.add(Admin(username="second", password_hash=hasher.hash(PASSWORD), role="viewer"))
    db.commit()
    client.headers["Origin"] = "http://testserver"
    assert sign_in(client, "second").status_code == 200
    second_cookie = client.cookies.get("session")
    second = db.query(Admin).filter_by(username="second").one()
    team.update_account(db, db.query(Admin).filter_by(username="first").one(), second, hasher, active=False)
    client.cookies.clear()
    client.cookies.set("session", second_cookie, path="/api")
    assert client.get("/api/admin/me").status_code == 401


def test_last_owner_cannot_be_removed(client, db):
    only = Admin(username="solo", password_hash=hasher.hash(PASSWORD))
    helper = Admin(username="helper2", password_hash=hasher.hash(PASSWORD), role="owner")
    db.add_all([only, helper])
    db.commit()
    team.update_account(db, only, helper, hasher, role="admin")
    try:
        team.update_account(db, helper, only, hasher, active=False)
        raise AssertionError("an admin must not block the owner")
    except team.TeamError as error:
        assert error.code == "above_you"
    try:
        team.delete_account(db, only, only)
        raise AssertionError("cannot delete yourself")
    except team.TeamError as error:
        assert error.code == "not_yourself"


def test_deleting_keeps_audit_history(admin_client, db):
    admin_client.post("/api/admin/team/accounts", json={"username": "worker", "password": PASSWORD, "role": "support"})
    worker = db.query(Admin).filter_by(username="worker").one()
    db.add(Audit(admin_id=worker.id, action="user.ban", target="1"))
    db.commit()
    assert admin_client.delete(f"/api/admin/team/accounts/{worker.id}").status_code == 200
    db.refresh(worker)
    assert not worker.active and worker.username.startswith("worker~")
    names = [a["username"] for a in admin_client.get("/api/admin/team").json()["accounts"]]
    assert "worker" not in names and not any("~" in n for n in names)
    # the name is free again
    assert admin_client.post("/api/admin/team/accounts", json={"username": "worker", "password": PASSWORD, "role": "support"}).status_code == 200


def test_roles_crud(admin_client):
    role = admin_client.post("/api/admin/team/roles", json={"name": "Ads", "permissions": ["ads.manage", "bots.view"]}).json()
    assert role["permissions"] == ["bots.view", "ads.manage"] and not role["builtin"]
    assert admin_client.put("/api/admin/team/roles/owner", json={"name": "x", "permissions": []}).json()["detail"] == "builtin_role"
    assert admin_client.post("/api/admin/team/roles", json={"name": "X", "permissions": ["fly"]}).json()["detail"] == "unknown_permission"
    admin_client.post("/api/admin/team/accounts", json={"username": "adman", "password": PASSWORD, "role": role["id"]})
    assert admin_client.delete(f"/api/admin/team/roles/{role['id']}").json()["detail"] == "role_in_use"
    updated = admin_client.put(f"/api/admin/team/roles/{role['id']}", json={"name": "Ads team", "permissions": ["ads.manage"]}).json()
    assert updated["name"] == "Ads team" and updated["accounts"] == 1


def test_every_admin_route_has_a_rule():
    owner = frozenset(team.PERMISSIONS)
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/admin"):
            continue
        sample = path.replace("{id}", "1").replace("{group}", "video").replace("{provider}", "stripe")
        for method in route.methods:
            assert team.allowed(owner, method, sample), (method, path)
    assert not team.allowed(owner, "GET", "/api/admin/not-a-real-endpoint")  # unknown = refused
