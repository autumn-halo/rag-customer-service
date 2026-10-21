"""文件路径工具：存储路径的可移植性处理。"""
from pathlib import Path

from app.config import settings


def resolve_stored_path(stored_path: str) -> Path:
    """数据库里存相对路径（相对于上传目录），保证数据目录整体可移植。

    兼容历史数据：早期版本存的是绝对路径，绝对路径直接使用。
    """
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return settings.upload_path / p
