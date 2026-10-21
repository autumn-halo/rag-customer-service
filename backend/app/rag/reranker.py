"""重排：对粗选出的候选片段做"复试"，把最相关的排前面。

接口抽象便于：测试时替换 FakeReranker、以后切换其他厂商模型。
阿里云已下架 gte-rerank，当前使用官方推荐的 qwen3-rerank
（走 compatible-api 通道，与对话/向量化的 compatible-mode 不是同一个地址）。
"""
import logging
from abc import ABC, abstractmethod

import httpx
import tenacity

from app.config import settings

logger = logging.getLogger(__name__)

RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        """返回 [(文档下标, 相关度分数), ...]，按分数降序。"""


class DashScopeReranker(Reranker):
    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        resp = httpx.post(
            RERANK_URL,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            json={
                "model": settings.model_rerank,
                "query": query,
                "documents": documents,
                "top_n": min(settings.rerank_top_n, len(documents)),
                "return_documents": False,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        return [(r["index"], r["relevance_score"]) for r in results]


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = DashScopeReranker()
    return _reranker
