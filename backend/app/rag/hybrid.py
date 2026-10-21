"""混合检索融合：RRF（Reciprocal Rank Fusion，倒数排名融合）。

向量检索与 BM25 的分数体系完全不同（余弦相似度 vs 词频统计），
无法直接相加。RRF 只看"名次"：两条检索路径里都排得靠前的片段得分更高。
score(d) = Σ 1 / (k + rank_i)，k 是平滑常数（常用 60）。
"""
from app.config import settings


def reciprocal_rank_fusion(
    vector_hits: list[dict],
    bm25_hits: list[dict],
    k: int | None = None,
) -> list[dict]:
    """融合两路命中，按 RRF 分数降序返回。两路的命中格式见 vectorstore/bm25 模块。"""
    k = k or settings.rrf_k
    fused: dict[str, dict] = {}
    for hits in (vector_hits, bm25_hits):
        for rank, hit in enumerate(hits):
            key = hit["chroma_id"]
            entry = fused.setdefault(
                key,
                {
                    "chunk_id": hit["chunk_id"],
                    "chroma_id": key,
                    "content": hit["content"],
                    "document_id": hit["document_id"],
                    "score": 0.0,
                },
            )
            entry["score"] += 1.0 / (k + rank + 1)
    return sorted(fused.values(), key=lambda x: x["score"], reverse=True)
