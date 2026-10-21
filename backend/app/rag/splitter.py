"""分块策略：把解析出的长文本切成适合检索的小段。

- 按字符数切（中文按 token 切受分词器影响，字符更稳定）
- 分隔符按中文习惯排序：段落 > 换行 > 句号类 > 分号 > 空格
- 相邻小段会合并到接近 chunk_size（避免一行一段导致碎片化，同时保留整行结构）
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", " "]


def make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )


def split_pages(pages) -> list[dict]:
    """把解析结果切成块，返回 [{content, metadata}, ...]。"""
    splitter = make_splitter()
    chunks: list[dict] = []
    for page in pages:
        meta = dict(page.metadata)
        meta["page_no"] = page.page_no
        pieces = splitter.split_text(page.text)
        for piece in _merge_small_pieces(pieces):
            chunks.append({"content": piece, "metadata": dict(meta)})
    return chunks


def _merge_small_pieces(pieces: list[str], max_size: int | None = None) -> list[str]:
    """相邻小段合并到接近 max_size，整行优先保留（Excel 行、FAQ 条目天然成块）。"""
    max_size = max_size or settings.chunk_size
    merged: list[str] = []
    buf = ""
    for piece in pieces:
        if len(buf) + len(piece) + 1 <= max_size:
            buf = f"{buf}\n{piece}" if buf else piece
        else:
            if buf:
                merged.append(buf)
            buf = piece
    if buf:
        merged.append(buf)
    return merged
