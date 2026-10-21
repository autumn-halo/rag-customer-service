"""BM25 关键词检索单元测试：索引重建与中文检索排序。"""
from app.database import SessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.rag import bm25


def _seed_chunks(contents: list[str]) -> list[Chunk]:
    with SessionLocal() as db:
        # chunk 有外键约束，先建所属用户与文档
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
        return chunks


def test_search_ranks_keyword_match_first():
    chunks = _seed_chunks(
        [
            "退货需在签收后 7 天内发起申请，逾期不予受理。",
            "现货商品会在 48 小时内发货，偏远地区除外。",
            "今天天气不错，适合出去散步。",
        ]
    )
    bm25.rebuild_index(chunks)

    hits = bm25.search("退货流程是什么", top_k=3)
    assert hits, "应命中关键词"
    assert hits[0]["content"].startswith("退货")


def test_no_match_returns_empty():
    bm25.rebuild_index(_seed_chunks(["这是苹果手机的商品介绍"]))
    assert bm25.search("量子力学", top_k=3) == []


def test_empty_index_returns_empty():
    bm25.rebuild_index([])
    assert bm25.search("任何问题", top_k=3) == []
