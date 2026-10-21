"""BM25 关键词检索：jieba 分词 + rank_bm25 全局内存索引。

- 与向量检索互补：商品型号、专有名词等精确词靠它兜住
- 全局索引由 chunks 表（事实来源）全量重建，重启后自动恢复
- 语料 10 万块以下重建是毫秒级，超过再考虑增量更新（README 有设计权衡说明）
"""
import threading

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk

_lock = threading.Lock()
_index: BM25Okapi | None = None
_docs: list[tuple[int, str, str, int]] = []  # [(chunk_id, chroma_id, content, document_id)]


def _tokenize(text: str) -> list[str]:
    return list(jieba.cut_for_search(text))


def rebuild_index(chunks: list[Chunk]) -> None:
    """从数据库 chunks 全量重建索引。"""
    global _index, _docs
    corpus = [_tokenize(c.content) for c in chunks]
    with _lock:
        _docs = [(c.id, c.chroma_id, c.content, c.document_id) for c in chunks]
        _index = BM25Okapi(corpus) if corpus else None


def rebuild_from_db(db: Session) -> None:
    """应用启动/文档变更后调用：从数据库恢复全局索引。"""
    rebuild_index(list(db.scalars(select(Chunk))))


def search(query: str, top_k: int) -> list[dict]:
    """关键词检索，返回统一格式的命中列表（分数为 BM25 原始分，只用于排序）。"""
    with _lock:
        if _index is None:
            return []
        scores = _index.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {
                "chunk_id": _docs[i][0],
                "chroma_id": _docs[i][1],
                "content": _docs[i][2],
                "document_id": _docs[i][3],
                "score": float(scores[i]),
            }
            for i in ranked
            if scores[i] > 0
        ]
