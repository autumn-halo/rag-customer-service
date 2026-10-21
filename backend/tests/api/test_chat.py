"""SSE 流式问答接口测试：事件协议与落库行为。"""
import json

from app.services import chat_service
from tests.fakes.fake_llm import FakeChatModel


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """把 SSE 响应文本解析成 [(event, data), ...]。"""
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        event = next((ln.split(": ", 1)[1] for ln in lines if ln.startswith("event: ")), "")
        data = next((ln.split(": ", 1)[1] for ln in lines if ln.startswith("data: ")), "")
        events.append((event, json.loads(data) if data else {}))
    return events


def test_stream_event_protocol(client, auth_headers, monkeypatch):
    answer = "根据测试资料，商品支持七天无理由退货。"
    monkeypatch.setattr(
        chat_service, "get_chat_model", lambda: FakeChatModel(answers=[answer], chunk_size=4)
    )
    headers = auth_headers("alice")

    resp = client.post("/api/chat/stream", json={"message": "退货政策？"}, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    kinds = [e[0] for e in events]

    assert kinds[0] == "meta"
    assert kinds[-1] == "done"
    assert all(k == "delta" for k in kinds[1:-1])

    # meta 事件携带会话 id，引用此时为空（阶段 4 起才有内容）
    meta = events[0][1]
    assert meta["cached"] is False
    assert meta["citations"] == []
    assert isinstance(meta["conversation_id"], int)

    # delta 拼接 = 完整答案
    full = "".join(e[1]["content"] for e in events[1:-1])
    assert full == answer

    # done 事件携带消息 id
    done = events[-1][1]
    assert isinstance(done["message_id"], int)


def test_stream_requires_login(client):
    resp = client.post("/api/chat/stream", json={"message": "你好"})
    assert resp.status_code == 401


def test_stream_empty_message_rejected(client, auth_headers):
    resp = client.post("/api/chat/stream", json={"message": ""}, headers=auth_headers())
    assert resp.status_code == 422
