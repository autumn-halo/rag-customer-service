"""检索编排：向量 + BM25 → RRF 融合 → 重排 → 最终引用片段。

实现 LangChain BaseRetriever 接口，可直接接入 LCEL 链
（满足 LangChain 硬性要求，也证明检索层的可替换性）。
重排失败时优雅降级为 RRF 排序，聊天不中断。
"""
import logging

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from app.config import settings
from app.rag import bm25, vectorstore
from app.rag.hybrid import reciprocal_rank_fusion
from app.rag.reranker import get_reranker

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """混合检索 + 重排。返回的 Document.metadata 携带引用所需全部字段。"""

    top_k: int = Field(default_factory=lambda: settings.final_top_k)
    vector_top_k: int = Field(default_factory=lambda: settings.vector_top_k)
    bm25_top_k: int = Field(default_factory=lambda: settings.bm25_top_k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,  # noqa: ARG002
    ) -> list[Document]:
        # 1. 双路粗选
        vector_hits = vectorstore.search(query, self.vector_top_k)
        bm25_hits = bm25.search(query, self.bm25_top_k)
        if not vector_hits and not bm25_hits:
            return []

        # 2. RRF 融合（分数只由名次决定），取前 10 进复试
        fused = reciprocal_rank_fusion(vector_hits, bm25_hits, settings.rrf_k)[:10]

        # 3. 重排复试（失败降级：保持 RRF 顺序，不带重排分）
        try:
            ranked = get_reranker().rerank(query, [h["content"] for h in fused])
        except Exception:  # noqa: BLE001
            logger.warning("重排失败，降级为 RRF 排序", exc_info=True)
            return [self._to_document(h) for h in fused[: self.top_k]]

        hits = []
        for idx, score in ranked[: self.top_k]:
            hit = fused[idx]
            hit["rerank_score"] = score
            hits.append(hit)
        return [self._to_document(h) for h in hits]

    @staticmethod
    def _to_document(hit: dict) -> Document:
        metadata = {k: v for k, v in hit.items() if k != "content"}
        return Document(page_content=hit["content"], metadata=metadata)


_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
