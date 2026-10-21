"""知识库管理接口（仅管理员）：上传、列表、详情、重解析、删除、分块预览。"""
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.config import settings
from app.database import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.schemas.document import ChunkOut, ChunkPage, DocumentOut, DocumentPage
from app.services import document_service, queue

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_admin)],  # 整个模块仅管理员可访问
)

ALLOWED_TYPES = {"pdf", "docx", "xlsx", "txt", "md"}


@router.post("/upload", status_code=201)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传一个或多个文档：立即保存并返回 pending，解析在后台进行。"""
    results = []
    max_bytes = settings.max_upload_mb * 1024 * 1024
    for f in files:
        ext = Path(f.filename or "").suffix.lower().lstrip(".")
        if ext not in ALLOWED_TYPES:
            results.append(
                {
                    "filename": f.filename,
                    "error": f"不支持的文件类型 .{ext}，仅支持 {', '.join(sorted(ALLOWED_TYPES))}",
                }
            )
            continue
        stored_name = f"{uuid4().hex}.{ext}"
        dest = settings.upload_path / stored_name
        size = 0
        try:
            with dest.open("wb") as out:
                while chunk := await f.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"文件超过 {settings.max_upload_mb}MB 上限",
                        )
                    out.write(chunk)
        except HTTPException:
            dest.unlink(missing_ok=True)
            raise
        doc = Document(
            filename=f.filename,
            stored_path=stored_name,  # 存相对路径：数据目录整体可移植（Windows ↔ Docker）
            file_type=ext,
            file_size=size,
            uploader_id=user.id,
            status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        queue.enqueue(doc.id)
        results.append({"document_id": doc.id, "filename": doc.filename, "status": "pending"})
    return results


@router.get("", response_model=DocumentPage)
def list_documents(
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
):
    items, total = document_service.list_documents(db, status=status, page=page, size=size)
    return DocumentPage(items=items, total=total, page=page, size=size)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.post("/{doc_id}/reprocess", status_code=204)
def reprocess_document(doc_id: int, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    document_service.reprocess_document(db, doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    document_service.delete_document_full(db, doc)


@router.get("/{doc_id}/chunks", response_model=ChunkPage)
def list_chunks(
    doc_id: int,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
):
    """分块预览（调试/演示用）。"""
    doc = document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    stmt = select(Chunk).where(Chunk.document_id == doc_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Chunk.chunk_index).offset((page - 1) * size).limit(size))
    return ChunkPage(
        items=[ChunkOut.model_validate(c) for c in rows],
        total=total,
        page=page,
        size=size,
    )
