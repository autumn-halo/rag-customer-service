"""单进程异步入库队列：上传立即返回，解析/向量化在后台执行。

- 2 个 worker 协程消费 document_id，阻塞操作统一扔进线程池
- 崩溃恢复：启动时把遗留的 processing 重置为 pending 并重新入队
- 不引 Celery：单机场景 30 行队列即可覆盖需求；量级增长后可平滑替换
  （任务抽象已隔离在本模块，README 有说明）
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.document import Document
from app.services.ingestion import ingest_document

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[int] | None = None
_worker_tasks: list[asyncio.Task] = []


def start_worker(workers: int = 2) -> None:
    global _queue, _worker_tasks
    _queue = asyncio.Queue()
    _worker_tasks = [asyncio.create_task(_run()) for _ in range(workers)]


async def stop_worker() -> None:
    for task in _worker_tasks:
        task.cancel()
    for task in _worker_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    _worker_tasks.clear()


def enqueue(document_id: int) -> None:
    if _queue is None:
        raise RuntimeError("入库队列尚未启动")
    _queue.put_nowait(document_id)


async def _run() -> None:
    while True:
        doc_id = await _queue.get()
        try:
            await asyncio.to_thread(_process, doc_id)
        except Exception:  # noqa: BLE001
            logger.exception("后台入库异常 doc=%s", doc_id)
        finally:
            _queue.task_done()


def _process(doc_id: int) -> None:
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        doc.status = "processing"
        db.commit()
        try:
            ingest_document(db, doc)
        except Exception:  # noqa: BLE001
            logger.exception("后台入库崩溃 doc=%s", doc_id)
            doc.status = "failed"
            doc.error_message = "后台处理异常，请重试"
            db.commit()


def recover_stale(db: Session) -> list[int]:
    """启动时把上次中断遗留的 processing 文档重置为 pending，返回待重入队的 id。"""
    stale = db.scalars(select(Document).where(Document.status == "processing")).all()
    for doc in stale:
        doc.status = "pending"
    db.commit()
    return [d.id for d in stale]
