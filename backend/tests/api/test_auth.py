"""用户体系接口测试：注册/登录/改密/权限。"""
from fastapi import HTTPException

from app.api.deps import require_admin
from app.models.user import User


def test_register_login_me(client):
    resp = client.post(
        "/api/auth/register", json={"username": "alice", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
    assert resp.json()["role"] == "user"

    resp = client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["username"] == "alice"

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


def test_register_duplicate_username_rejected(client):
    client.post("/api/auth/register", json={"username": "alice", "password": "secret123"})
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "secret456"})
    assert resp.status_code == 400
    assert "已被注册" in resp.json()["detail"]


def test_register_username_too_short_rejected(client):
    resp = client.post("/api/auth/register", json={"username": "ab", "password": "secret123"})
    assert resp.status_code == 422


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"username": "alice", "password": "secret123"})
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrong-pass"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "secret123"})
    assert resp.status_code == 401


def test_me_without_token_rejected(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_tampered_token_rejected(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.token.value"})
    assert resp.status_code == 401


def test_admin_seeded_and_can_login(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"


def test_change_password_flow(client, register_and_login):
    token = register_and_login("alice")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/users/me/password",
        json={"old_password": "secret123", "new_password": "newpass456"},
        headers=headers,
    )
    assert resp.status_code == 204

    # 旧密码失效，新密码生效
    assert client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret123"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"username": "alice", "password": "newpass456"}
    ).status_code == 200


def test_change_password_wrong_old_password(client, register_and_login):
    token = register_and_login("alice")
    resp = client.put(
        "/api/users/me/password",
        json={"old_password": "wrong-old", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "原密码不正确" in resp.json()["detail"]


def test_require_admin_blocks_normal_user():
    normal = User(username="u", password_hash="x", role="user")
    try:
        require_admin(normal)
        raise AssertionError("应当抛出 403")
    except HTTPException as e:
        assert e.status_code == 403


def test_require_admin_allows_admin():
    admin = User(username="a", password_hash="x", role="admin")
    assert require_admin(admin) is admin
