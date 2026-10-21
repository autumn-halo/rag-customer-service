"""一键验证阿里云百炼 API Key：依次测试对话(流式)、向量化、重排三项能力。

用法：python scripts/check_dashscope.py
"""
import sys
from pathlib import Path

# 让脚本能 import backend/app 下的模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

from app.config import settings  # noqa: E402

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 对话/向量化（OpenAI 兼容）
RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"  # 重排（另一条通道）


def _client() -> OpenAI:
    return OpenAI(api_key=settings.dashscope_api_key, base_url=BASE_URL)


def check_chat() -> None:
    """[1/3] 对话模型：流式返回一句自我介绍。"""
    client = _client()
    stream = client.chat.completions.create(
        model=settings.model_chat,
        messages=[{"role": "user", "content": "请用一句话介绍你自己"}],
        stream=True,
    )
    text = "".join(chunk.choices[0].delta.content or "" for chunk in stream)
    assert text.strip(), "对话模型未返回任何内容"
    print(f"[1/3] 对话 OK（{settings.model_chat}，流式）：{text.strip()[:40]}...")


def check_embedding() -> None:
    """[2/3] 向量化模型：返回维度必须与配置一致。"""
    client = _client()
    resp = client.embeddings.create(
        model=settings.model_embedding,
        input=["这是一段用于验证向量化接口的测试文本"],
        dimensions=settings.embedding_dimensions,
    )
    dim = len(resp.data[0].embedding)
    assert dim == settings.embedding_dimensions, f"向量维度 {dim} 与配置 {settings.embedding_dimensions} 不符"
    print(f"[2/3] 向量化 OK（{settings.model_embedding}，{dim} 维）")


def check_rerank() -> None:
    """[3/3] 重排模型：三条文档打分，最相关的应排第一。"""
    resp = httpx.post(
        RERANK_URL,
        headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
        json={
            "model": settings.model_rerank,
            "query": "退货流程是什么",
            "documents": ["退货需在签收后 7 天内发起申请", "今天天气不错", "商品支持七天无理由退货"],
            "top_n": 2,
            "return_documents": True,
        },
        timeout=30,
    )
    assert resp.status_code == 200, f"重排失败：HTTP {resp.status_code} {resp.text[:200]}"
    results = resp.json()["results"]
    assert results, "重排未返回任何结果"
    top = results[0]
    print(
        f"[3/3] 重排 OK（{settings.model_rerank}）：最相关='{top['document']['text']}'"
        f"（score={top['relevance_score']}）"
    )


if __name__ == "__main__":
    if not settings.dashscope_api_key:
        sys.exit("❌ 未配置 DASHSCOPE_API_KEY，请先复制 .env.example 为 backend/.env 并填入 Key")
    try:
        check_chat()
        check_embedding()
        check_rerank()
        print("\n✅ 三项验证全部通过，DashScope 配置正确！")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"❌ 验证失败：{e}")
