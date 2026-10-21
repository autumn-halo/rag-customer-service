"""对话模型工厂（RAG 检索链在阶段 4 接入）。"""
from langchain_openai import ChatOpenAI

from app.config import settings

# DashScope 的 OpenAI 兼容模式入口：换厂商只改这里或 .env
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def get_chat_model() -> ChatOpenAI:
    """对话模型：流式输出，最后一帧携带 token 用量（用于成本统计）。"""
    return ChatOpenAI(
        model=settings.model_chat,
        api_key=settings.dashscope_api_key,
        base_url=DASHSCOPE_BASE_URL,
        temperature=0.3,
        streaming=True,
        stream_usage=True,
    )
