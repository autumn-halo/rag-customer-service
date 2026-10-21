"""向量化：把文字翻译成一串数字坐标（向量），意思相近的文字坐标也相近。"""
from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.rag.chain import DASHSCOPE_BASE_URL

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """单例复用（内部有连接池）；换模型只改 .env。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.model_embedding,
            api_key=settings.dashscope_api_key,
            base_url=DASHSCOPE_BASE_URL,
            dimensions=settings.embedding_dimensions,
            # 关键：新版 langchain-openai 默认把文字预分词成数字编号再发送
            # （OpenAI 官方接口支持），但 DashScope 兼容模式只收原始文字，
            # 关闭预分词改为发送原文（官方文档推荐非 OpenAI 厂商如此配置）
            check_embedding_ctx_length=False,
        )
    return _embeddings
