"""入库流水线：解析 → 分块 → 写库 → 批量向量化 → 写 Chroma → 重建 BM25。"""
import logging
from pathlib import Path

import tenacity
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.rag import bm25, vectorstore
from app.rag.embeddings import get_embeddings
from app.rag.loader import DocumentParseError, parse_document
from app.rag.splitter import split_pages

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 25


@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embeddings().embed_documents(texts)


def ingest_document(db: Session, doc: Document) -> None:
    """处理一个文档；任何失败都会标记 failed 并记录可读原因，不抛出。"""
    try:
        _do_ingest(db, doc)
    except DocumentParseError as e:
        doc.status = "failed"
        doc.error_message = str(e)
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception("文档入库失败 doc=%s", doc.id)
        doc.status = "failed"
        doc.error_message = f"入库失败：{e}"
        db.commit()


def _do_ingest(db: Session, doc: Document) -> None:
    # 1. 解析
    pages = parse_document(Path(doc.stored_path), doc.file_type)
    # 2. 分块
    pieces = split_pages(pages)
    if not pieces:
        raise DocumentParseError("文档切分后没有有效内容")
    if len(pieces) > settings.max_chunks_per_doc:
        raise DocumentParseError(
            f"文档过大（切出 {len(pieces)} 块，上限 {settings.max_chunks_per_doc}）"
        )
    # 3. 写 chunks 表（事实来源；重复处理前会先清旧数据，保证幂等）
    chunks = [
        Chunk(
            document_id=doc.id,
            chunk_index=i,
            content=p["content"],
            meta=p["metadata"],
            chroma_id=f"doc_{doc.id}_chunk_{i}",
        )
        for i, p in enumerate(pieces)
    ]
    db.add_all(chunks)
    db.commit()
    for c in chunks:
        db.refresh(c)
    # 4. 批量向量化 + 写 Chroma（分批控制 API 并发与单次载荷）
    texts = [c.content for c in chunks]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        vectors.extend(_embed_texts(texts[i : i + EMBED_BATCH_SIZE]))
    vectorstore.add_chunks(chunks, vectors)
    # 5. 重建 BM25（从 DB 全量，chunks 表是事实来源）
    bm25.rebuild_from_db(db)
    # 6. 成功
    doc.status = "success"
    doc.chunk_count = len(chunks)
    db.commit()
