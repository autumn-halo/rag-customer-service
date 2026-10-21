"""RAG 问答链路测试：引用快照、兜底阈值、缓存命中（全程假模型零 API 消耗）。"""
import json

from langchain_core.documents import Document

from app.database import SessionLocal
from app.models.document import Document as DocModel
from app.rag import prompt
from app.services import cache, chat_service
from tests.fakes.fake_llm import FakeChatModel


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        event = next((ln.split(": ", 1)[1] for ln in lines if ln.startswith("event: ")), "")
        data = next((ln.split(": ", 1)[1] for ln in lines if ln.startswith("data: ")), "")
        events.append((event, json.loads(data) if data else {}))
    return events


def _seed_document(title: str = "退货政策.pdf") -> DocModel:
    with SessionLocal() as db:
        doc = DocModel(
            filename=title,
            stored_path="unused.pdf",
            file_type="pdf",
            file_size=1,
            uploader_id=1,
            status="success",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc


def _patch_retriever(monkeypatch, docs: list[Document]):
    class _FixedRetriever:
        def invoke(self, query):  # noqa: ARG002
            return docs

    monkeypatch.setattr(chat_service, "get_retriever", lambda: _FixedRetriever())


def test_answer_with_citations(client, auth_headers, monkeypatch):
    cache.get_cache().clear()
    doc = _seed_document()
    chunk = Document(
        page_content="退货需在签收后 7 天内发起申请。",
        metadata={
            "chunk_id": 1,
            "chroma_id": "doc_1_chunk_0",
            "document_id": doc.id,
            "rerank_score": 0.9,
        },
    )
    _patch_retriever(monkeypatch, [chunk])
    monkeypatch.setattr(
        chat_service, "get_chat_model",
        lambda: FakeChatModel(answers=["根据资料[1]，退货需在签收后 7 天内申请。"]),
    )

    headers = auth_headers("alice")  # 只注册一次，多次复用
    resp = client.post(
        "/api/chat/stream", json={"message": "退货流程是什么"}, headers=headers
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    meta = events[0][1]
    assert meta["citations"], "meta 事件应携带引用快照"
    c = meta["citations"][0]
    assert c["index"] == 1
    assert c["document_title"] == "退货政策.pdf"
    assert c["score"] == 0.9
    assert c["content"].startswith("退货")

    # 助手消息落库时引用快照持久化
    conv_id = meta["conversation_id"]
    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=headers).json()
    assistant = [m for m in msgs if m["role"] == "assistant"][0]
    assert assistant["references"][0]["document_title"] == "退货政策.pdf"


def test_product_question_without_docs_falls_back(client, auth_headers, monkeypatch):
    """商品咨询但知识库没有任何资料 → 兜底话术，不调模型。"""
    cache.get_cache().clear()
    _patch_retriever(monkeypatch, [])  # 检索返回空

    class _BoomLLM:
        async def astream(self, messages):
            raise AssertionError("兜底路径不应调用大模型")

    monkeypatch.setattr(chat_service, "get_chat_model", lambda: _BoomLLM())

    resp = client.post(
        "/api/chat/stream", json={"message": "退货流程是什么"}, headers=auth_headers("alice")
    )
    events = _parse_sse(resp.text)
    assert events[0][1]["citations"] == []
    full = "".join(e[1]["content"] for e in events if e[0] == "delta")
    assert full == prompt.FALLBACK_ANSWER


def test_low_score_falls_back_without_llm(client, auth_headers, monkeypatch):
    cache.get_cache().clear()
    doc = _seed_document()
    chunk = Document(
        page_content="与问题无关的内容",
        metadata={"chunk_id": 1, "chroma_id": "c", "document_id": doc.id, "rerank_score": 0.01},
    )
    _patch_retriever(monkeypatch, [chunk])

    class _BoomLLM:
        async def astream(self, messages):
            raise AssertionError("兜底路径不应调用大模型")

    monkeypatch.setattr(chat_service, "get_chat_model", lambda: _BoomLLM())

    resp = client.post(
        "/api/chat/stream", json={"message": "退货流程是什么"}, headers=auth_headers("alice")
    )
    events = _parse_sse(resp.text)
    assert events[0][1]["citations"] == []  # 兜底不带引用
    full = "".join(e[1]["content"] for e in events if e[0] == "delta")
    assert full == prompt.FALLBACK_ANSWER


def test_meta_question_goes_plain_path_without_retrieval(client, auth_headers, monkeypatch):
    """闲聊问题（如"你是什么大模型"）不检索知识库，直接自由对话。"""
    cache.get_cache().clear()

    class _BoomRetriever:
        def invoke(self, query):  # noqa: ARG002
            raise AssertionError("闲聊问题不应触发检索")

    monkeypatch.setattr(chat_service, "get_retriever", lambda: _BoomRetriever())
    monkeypatch.setattr(
        chat_service, "get_chat_model",
        lambda: FakeChatModel(answers=["我是通义千问，阿里巴巴自研的大语言模型。"]),
    )

    resp = client.post(
        "/api/chat/stream", json={"message": "你是什么大模型"}, headers=auth_headers("alice")
    )
    events = _parse_sse(resp.text)
    assert events[0][1]["citations"] == []  # 自由对话不带引用
    full = "".join(e[1]["content"] for e in events if e[0] == "delta")
    assert "通义千问" in full


def test_cache_hit_second_time(client, auth_headers, monkeypatch):
    cache.get_cache().clear()
    calls = {"n": 0}

    class _CountingLLM:
        async def astream(self, messages):
            calls["n"] += 1
            yield type("Chunk", (), {"content": "首次生成的回答。", "usage_metadata": None})()

    monkeypatch.setattr(chat_service, "get_chat_model", lambda: _CountingLLM())

    question = "缓存测试专用问题"
    headers = auth_headers("alice")  # 只注册一次，多次复用
    for _ in range(2):
        resp = client.post(
            "/api/chat/stream", json={"message": question}, headers=headers
        )
        assert resp.status_code == 200

    # 第三次请求：第一次生成后两次都命中缓存（meta.cached=true），模型只被调用一次
    second = client.post(
        "/api/chat/stream", json={"message": question}, headers=headers
    )
    events = _parse_sse(second.text)
    assert calls["n"] == 1
    assert events[0][1]["cached"] is True
    full = "".join(e[1]["content"] for e in events if e[0] == "delta")
    assert full == "首次生成的回答。"
