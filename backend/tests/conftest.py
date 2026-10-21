"""pytest 全局配置：测试全程使用临时数据库，绝不触碰真实数据与真实 API。

环境变量必须在导入 app 之前设置（config 在导入时读取一次）。
"""
import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="rag_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["CHROMA_DIR"] = f"{_tmp_dir}/chroma"
os.environ["UPLOAD_DIR"] = f"{_tmp_dir}/uploads"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
os.environ["DASHSCOPE_API_KEY"] = ""  # 测试绝不调用真实大模型 API

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    """每个测试前重建全部表，测试之间互不影响。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    """测试客户端（with 语法触发 lifespan：建表 + 播种管理员 admin/123456）。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def register_and_login(client):
    """快捷方法：注册并登录一个新用户，返回 Bearer 令牌。"""

    def _fn(username: str, password: str = "secret123") -> str:
        resp = client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        resp = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _fn


@pytest.fixture()
def auth_headers(register_and_login):
    """返回带普通用户令牌的请求头。"""

    def _fn(username: str = "alice") -> dict:
        token = register_and_login(username)
        return {"Authorization": f"Bearer {token}"}

    return _fn


@pytest.fixture()
def admin_headers(client):
    """返回带管理员令牌的请求头（admin/123456 由 lifespan 自动播种）。"""
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "123456"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
