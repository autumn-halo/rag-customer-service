"""文档管理：列表查询、删除（清库/向量/磁盘三处）、重新解析。"""
import logging
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.rag import bm25, vectorstore
from app.services import queue

logger = logging.getLogger(__name__)


def list_documents(
    db: Session, status: str | None = None, page: int = 1, size: int = 20
) -> tuple[list[Document], int]:
    stmt = select(Document)
    if status:
        stmt = stmt.where(Document.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Document.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return list(rows), total


def get_document(db: Session, doc_id: int) -> Document | None:
    return db.get(Document, doc_id)


def delete_document_full(db: Session, doc: Document) -> None:
    """三处一起删：Chroma 向量、DB（chunks 级联）、磁盘文件；然后重建 BM25。"""
    vectorstore.delete_document(doc.id)
    db.delete(doc)
    db.commit()
    bm25.rebuild_from_db(db)
    try:
        Path(doc.stored_path).unlink(missing_ok=True)
    except OSError:  # noqa: BLE001
        logger.warning("删除磁盘文件失败: %s", doc.stored_path)


def reprocess_document(db: Session, doc: Document) -> None:
    """重新解析：先清旧 chunks 与向量，再入队重跑（幂等）。"""
    vectorstore.delete_document(doc.id)
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    doc.status = "pending"
    doc.error_message = None
    doc.chunk_count = 0
    db.commit()
    bm25.rebuild_from_db(db)
    queue.enqueue(doc.id)
