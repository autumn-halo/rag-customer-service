"""RRF 融合单元测试：数学正确性。"""
from app.rag.hybrid import reciprocal_rank_fusion


def _hit(chroma_id: str) -> dict:
    return {
        "chunk_id": None,
        "chroma_id": chroma_id,
        "content": chroma_id,
        "document_id": 1,
        "score": 0.0,
    }


def test_both_paths_hit_rank_first():
    # 两路都排第一的片段，RRF 分数最高
    vector = [_hit("a"), _hit("b")]
    bm25 = [_hit("a"), _hit("c")]
    fused = reciprocal_rank_fusion(vector, bm25, k=60)
    assert fused[0]["chroma_id"] == "a"
    # score(a) = 1/61 + 1/61 = 2/61
    assert abs(fused[0]["score"] - 2 / 61) < 1e-9


def test_single_path_hit_included():
    fused = reciprocal_rank_fusion([_hit("only_vector")], [], k=60)
    assert len(fused) == 1
    assert fused[0]["score"] == 1 / 61


def test_empty_inputs():
    assert reciprocal_rank_fusion([], [], k=60) == []


def test_deduplicates_same_chunk():
    vector = [_hit("a")]
    bm25 = [_hit("a")]
    fused = reciprocal_rank_fusion(vector, bm25, k=60)
    assert len(fused) == 1  # 同一片段只保留一条并累加分数
