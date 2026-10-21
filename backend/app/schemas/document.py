"""知识库文档接口的请求/响应数据结构。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    error_message: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    size: int


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    content: str
    meta: dict | None = None


class ChunkPage(BaseModel):
    items: list[ChunkOut]
    total: int
    page: int
    size: int
