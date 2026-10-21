"""检索链路集成测试：真实 Chroma（内存）+ 真实 BM25 + 假向量化/假重排。"""
import pytest

from app.database import SessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.rag import bm25, vectorstore
from app.rag import retriever as retriever_module
from app.rag.retriever import HybridRetriever
from tests.fakes.fake_embeddings import FakeEmbeddings
from tests.fakes.fake_reranker import FakeReranker


@pytest.fixture()
def seeded_chroma(chroma_mem, monkeypatch):
    contents = [
        "退货需在签收后 7 天内发起申请，逾期不予受理。",
        "现货商品会在 48 小时内发货，偏远地区除外。",
        "今天天气不错，适合出去散步。",
    ]
    with SessionLocal() as db:
        user = User(username="tester", password_hash="x", role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        doc = Document(filename="t.txt", stored_path="x", file_type="txt", uploader_id=user.id)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        chunks = [
            Chunk(document_id=doc.id, chunk_index=i, content=c, chroma_id=f"doc_{doc.id}_chunk_{i}")
            for i, c in enumerate(contents)
        ]
        db.add_all(chunks)
        db.commit()
        for c in chunks:
            db.refresh(c)
        vectors = [FakeEmbeddings().embed_query(c.content) for c in chunks]
        vectorstore.add_chunks(chunks, vectors)
        bm25.rebuild_index(chunks)
    # 注意：要替换 retriever 命名空间里的工厂引用
    monkeypatch.setattr(retriever_module, "get_reranker", lambda: FakeReranker())
    yield


def test_hybrid_retrieval_ranks_relevant_first(seeded_chroma):
    docs = HybridRetriever().invoke("退货流程是什么")
    assert docs, "应命中片段"
    assert "退货" in docs[0].page_content
    # 元数据携带引用所需的全部字段
    assert docs[0].metadata["document_id"] == 1
    assert docs[0].metadata["chunk_id"] is not None
    assert "rerank_score" in docs[0].metadata
    assert docs[0].metadata["rerank_score"] > 0


def test_irrelevant_query_gets_zero_rerank_score(seeded_chroma):
    # 检索器不负责阈值过滤（那是 chat_service 的兜底职责），
    # 但相关度分数必须如实反映"不相关"
    docs = HybridRetriever().invoke("量子力学")
    assert docs[0].metadata["rerank_score"] == 0.0


def test_rerank_failure_degrades_to_rrf_order(seeded_chroma, monkeypatch):
    class _BoomReranker:
        def rerank(self, query, documents):
            raise RuntimeError("rerank API 挂了")

    monkeypatch.setattr(retriever_module, "get_reranker", lambda: _BoomReranker())
    docs = HybridRetriever().invoke("退货流程是什么")
    assert docs, "重排失败时仍应返回 RRF 排序结果"
    assert "rerank_score" not in docs[0].metadata  # 降级路径不带重排分
