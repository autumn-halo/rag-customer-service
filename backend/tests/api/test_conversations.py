"""会话管理接口测试：CRUD、多用户隔离、消息记录。"""
from app.services import chat_service
from tests.fakes.fake_llm import FakeChatModel


def _create_conv(client, headers, title=None):
    body = {"title": title} if title else {}
    resp = client.post("/api/conversations", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_list_conversations(client, auth_headers):
    headers = auth_headers("alice")
    c1 = _create_conv(client, headers, "会话一")
    c2 = _create_conv(client, headers)

    resp = client.get("/api/conversations", headers=headers)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert c2["id"] in ids and c1["id"] in ids
    # 默认标题
    assert c2["title"] == "新会话"


def test_rename_conversation(client, auth_headers):
    headers = auth_headers("alice")
    conv = _create_conv(client, headers)

    resp = client.patch(
        f"/api/conversations/{conv['id']}", json={"title": "改名了"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "改名了"


def test_delete_conversation(client, auth_headers):
    headers = auth_headers("alice")
    conv = _create_conv(client, headers)

    resp = client.delete(f"/api/conversations/{conv['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/api/conversations", headers=headers).json() == []


def test_user_cannot_access_others_conversation(client, auth_headers):
    alice = auth_headers("alice")
    bob = auth_headers("bob")
    conv = _create_conv(client, alice)

    # 他人访问一律 404（不泄露会话是否存在）
    assert client.get(f"/api/conversations/{conv['id']}/messages", headers=bob).status_code == 404
    assert client.patch(
        f"/api/conversations/{conv['id']}", json={"title": "抢名"}, headers=bob
    ).status_code == 404
    assert client.delete(f"/api/conversations/{conv['id']}", headers=bob).status_code == 404


def test_conversations_list_only_own(client, auth_headers):
    alice = auth_headers("alice")
    bob = auth_headers("bob")
    _create_conv(client, alice, "alice 的会话")

    resp = client.get("/api/conversations", headers=bob)
    assert resp.status_code == 200
    assert resp.json() == []


def test_chat_creates_conversation_with_auto_title(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        chat_service, "get_chat_model", lambda: FakeChatModel(answers=["好的，这是回答。"])
    )
    headers = auth_headers("alice")
    question = "请问你们的退货政策是怎样的？"

    resp = client.post("/api/chat/stream", json={"message": question}, headers=headers)
    assert resp.status_code == 200

    # 会话自动创建，标题取问题前 20 字
    convs = client.get("/api/conversations", headers=headers).json()
    assert len(convs) == 1
    assert convs[0]["title"] == question[:20]

    # 消息记录：一问一答都已落库
    msgs = client.get(f"/api/conversations/{convs[0]['id']}/messages", headers=headers).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == question
    assert msgs[1]["content"] == "好的，这是回答。"


def test_chat_appends_to_existing_conversation(client, auth_headers, monkeypatch):
    # 同一个假模型实例：两次调用依次吐出两个预设答案
    fake = FakeChatModel(answers=["回答一", "回答二"])
    monkeypatch.setattr(chat_service, "get_chat_model", lambda: fake)
    headers = auth_headers("alice")

    resp = client.post("/api/chat/stream", json={"message": "第一个问题"}, headers=headers)
    assert resp.status_code == 200
    conv_id = client.get("/api/conversations", headers=headers).json()[0]["id"]

    resp = client.post(
        "/api/chat/stream", json={"conversation_id": conv_id, "message": "第二个问题"},
        headers=headers,
    )
    assert resp.status_code == 200

    convs = client.get("/api/conversations", headers=headers).json()
    assert len(convs) == 1  # 没有新建会话
    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=headers).json()
    assert [m["content"] for m in msgs] == ["第一个问题", "回答一", "第二个问题", "回答二"]


def test_chat_with_others_conversation_gets_error_event(client, auth_headers, monkeypatch):
    monkeypatch.setattr(chat_service, "get_chat_model", lambda: FakeChatModel())
    alice = auth_headers("alice")
    bob = auth_headers("bob")

    resp = client.post("/api/chat/stream", json={"message": "你好"}, headers=alice)
    conv_id = client.get("/api/conversations", headers=alice).json()[0]["id"]

    resp = client.post(
        "/api/chat/stream", json={"conversation_id": conv_id, "message": "偷看"}, headers=bob
    )
    assert resp.status_code == 200
    assert "event: error" in resp.text
    assert "会话不存在" in resp.text
