"""分块策略单元测试：长度控制、中文分隔符、小块合并、元数据传递。"""
from types import SimpleNamespace

from app.config import settings
from app.rag.splitter import _merge_small_pieces, split_pages


def _pages(text: str, **meta) -> list:
    return [SimpleNamespace(page_no=1, text=text, metadata=meta)]


def test_all_chunks_within_chunk_size(monkeypatch):
    monkeypatch.setattr(settings, "chunk_size", 100)
    monkeypatch.setattr(settings, "chunk_overlap", 20)
    text = "第一句话。" * 60
    chunks = split_pages(_pages(text))
    assert chunks
    assert all(len(c["content"]) <= 100 for c in chunks)


def test_small_lines_merge_into_one_chunk():
    # 短行合并：避免"一行一段"碎片化
    merged = _merge_small_pieces(["行1", "行2", "行3"], max_size=100)
    assert merged == ["行1\n行2\n行3"]


def test_oversized_piece_starts_new_chunk():
    merged = _merge_small_pieces(["a" * 90, "b" * 90], max_size=100)
    assert merged == ["a" * 90, "b" * 90]


def test_split_respects_sentence_separator(monkeypatch):
    monkeypatch.setattr(settings, "chunk_size", 500)
    monkeypatch.setattr(settings, "chunk_overlap", 80)
    text = "退货需在签收后7天内申请。\n发货时间一般为48小时。"
    chunks = split_pages(_pages(text))
    # 两句话都很短，应合并进同一个块而不是被空格/句号拆散
    assert len(chunks) == 1


def test_metadata_carried_into_chunks():
    chunks = split_pages(_pages("内容测试。", sheet="商品表"))
    assert chunks[0]["metadata"]["sheet"] == "商品表"
    assert chunks[0]["metadata"]["page_no"] == 1
