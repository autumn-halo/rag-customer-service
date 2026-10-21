"""问答接口的请求数据结构。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int | None = None  # 为空则自动新建会话
    message: str = Field(min_length=1, max_length=2000)
