"""聊天编排：检索 → 路由分流 → 流式回答 → 引用与消息落库。

主流程（检索优先、关键词兜底）：
1. 会话归属校验（新建则自动建会话，标题取首问前 20 字），保存用户消息
2. 检索知识库（任何措辞的商品问题都由检索相关度说话）
3. 路由分流：
   - 相关度 ≥ 阈值 → 严格模式：依据资料作答、强制 [n] 引用
   - 相关度不足 + 商品关键词 → 兜底话术（不调 LLM，防瞎编）
   - 相关度不足 + 非商品 → 自由对话（"你是什么大模型"这类问题自然回答）
4. 答案缓存：相同问题 + 相同引用集合 → 秒回
5. 流式生成 → 保存助手消息（含引用快照与 token 用量）→ 写缓存
"""
import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.base import utcnow
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.user import User
from app.rag import intent, prompt
from app.rag.chain import get_chat_model
from app.rag.retriever import get_retriever
from app.services import cache

logger = logging.getLogger(__name__)

STREAM_CHUNK_SIZE = 20  # 缓存命中/兜底话术按此字符数模拟流式输出


class ConversationNotFoundError(Exception):
    """会话不存在或不属于当前用户。"""


def _get_or_create_conversation(
    db: Session, user: User, conversation_id: int | None, question: str
) -> Conversation:
    if conversation_id is not None:
        conv = db.get(Conversation, conversation_id)
        # 别人的会话按"不存在"处理，避免泄露会话是否存在
        if conv is None or conv.user_id != user.id:
            raise ConversationNotFoundError("会话不存在")
        return conv
    # 新会话：标题取首条提问的前 20 个字
    title = question.strip()[:20] or "新会话"
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _load_history(db: Session, conversation_id: int, turns: int) -> list[dict]:
    """取最近 N 轮对话（按时间正序返回）。"""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(turns * 2)
    )
    rows = db.scalars(stmt).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def _save_assistant(
    db: Session, conv: Conversation, content: str, references: list[dict], token_count: int | None
) -> Message:
    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=content,
        references=references or None,
        token_count=token_count,
    )
    db.add(msg)
    conv.updated_at = utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def _build_references(db: Session, docs: list) -> list[dict]:
    """把检索结果转成引用快照（前端与提示词共用），编号与 prompt 中 [n] 一一对应。"""
    if not docs:
        return []
    doc_ids = {d.metadata["document_id"] for d in docs if d.metadata.get("document_id")}
    titles = {
        d.id: d.filename
        for d in db.scalars(select(Document).where(Document.id.in_(doc_ids)))
    } if doc_ids else {}
    references = []
    for i, d in enumerate(docs, start=1):
        references.append(
            {
                "index": i,
                "chunk_id": d.metadata.get("chunk_id"),
                "document_id": d.metadata.get("document_id"),
                "document_title": titles.get(d.metadata.get("document_id"), "未知文档"),
                "score": round(float(d.metadata.get("rerank_score", 0.0)), 4),
                "content": d.page_content,
            }
        )
    return references


def _meta_event(cached: bool, citations: list[dict], conversation_id: int) -> dict:
    return {
        "event": "meta",
        "data": {"cached": cached, "citations": citations, "conversation_id": conversation_id},
    }


async def _stream_text(text: str):
    """把一段完整文本切成小块模拟流式输出（缓存命中/兜底话术用）。"""
    for i in range(0, len(text), STREAM_CHUNK_SIZE):
        yield {"event": "delta", "data": {"content": text[i : i + STREAM_CHUNK_SIZE]}}


async def _stream_llm(
    db: Session,
    conv: Conversation,
    messages: list,
    references: list[dict],
    cache_key: str,
):
    """调用模型流式生成：失败转为 error 事件；成功后落库并写缓存。"""
    llm = get_chat_model()
    full_text = ""
    token_count = None
    try:
        async for chunk in llm.astream(messages):
            text = chunk.content or ""
            full_text += text
            yield {"event": "delta", "data": {"content": text}}
            usage = getattr(chunk, "usage_metadata", None)
            if usage:
                token_count = usage.get("total_tokens")
    except Exception:  # noqa: BLE001
        logger.exception("模型生成失败")
        yield _sse_error("模型服务暂不可用，请稍后重试")
        return
    msg = _save_assistant(db, conv, full_text, references, token_count)
    cache.get_cache().set(cache_key, full_text, settings.cache_ttl_seconds)
    yield _sse_done(msg.id, token_count)


async def stream_chat(
    db: Session,
    user: User,
    conversation_id: int | None,
    question: str,
):
    """流式问答主流程，逐个产出 SSE 事件 {event, data}。"""
    conv = _get_or_create_conversation(db, user, conversation_id, question)

    # 1. 保存用户消息
    db.add(Message(conversation_id=conv.id, role="user", content=question))
    conv.updated_at = utcnow()
    db.commit()

    history_text = prompt.format_history(_load_history(db, conv.id, settings.history_turns))
    plain_cache_key = cache.chat_cache_key(settings.model_chat, question, [])

    # 2. 检索知识库（检索异常时中断并返回"系统繁忙"，绝不让聊天 500）
    try:
        docs = await asyncio.to_thread(get_retriever().invoke, question)
    except Exception:  # noqa: BLE001
        logger.exception("检索链路异常")
        yield _sse_error("系统繁忙，请稍后重试")
        return

    chroma_ids = [d.metadata.get("chroma_id") or "" for d in docs]
    references = prompt.fit_context(_build_references(db, docs), settings.context_max_chars)
    cache_key = cache.chat_cache_key(settings.model_chat, question, chroma_ids)

    # 3. 路由分流：检索相关度优先，关键词兜底
    best_score = docs[0].metadata.get("rerank_score") if docs else None
    # 重排降级时 best_score 为 None：视为相关（保留 RRF 排序结果，不误伤）
    relevant = bool(docs) and (best_score is None or best_score >= settings.rerank_threshold)

    if not relevant and not intent.is_product_question(question):
        # 3a. 自由对话：检索不到相关资料且不是商品问题（如"你是什么大模型"）
        cached_text = cache.get_cache().get(plain_cache_key)
        if cached_text is not None:
            yield _meta_event(cached=True, citations=[], conversation_id=conv.id)
            async for event in _stream_text(cached_text):
                yield event
            msg = _save_assistant(db, conv, cached_text, [], None)
            yield _sse_done(msg.id, None)
            return
        yield _meta_event(cached=False, citations=[], conversation_id=conv.id)
        messages = [
            SystemMessage(content=prompt.SYSTEM_PROMPT_PLAIN),
            HumanMessage(content=prompt.build_plain_user_prompt(history_text, question)),
        ]
        async for event in _stream_llm(db, conv, messages, [], plain_cache_key):
            yield event
        return

    if not relevant:
        # 3b. 兜底：商品咨询但无相关资料 → 不调 LLM，直接固定话术
        yield _meta_event(cached=False, citations=[], conversation_id=conv.id)
        async for event in _stream_text(prompt.FALLBACK_ANSWER):
            yield event
        msg = _save_assistant(db, conv, prompt.FALLBACK_ANSWER, [], None)
        yield _sse_done(msg.id, None)
        return

    # 3c. 严格模式：依据参考资料作答，强制引用格式
    cached_text = cache.get_cache().get(cache_key)
    if cached_text is not None:
        yield _meta_event(cached=True, citations=references, conversation_id=conv.id)
        async for event in _stream_text(cached_text):
            yield event
        msg = _save_assistant(db, conv, cached_text, references, None)
        yield _sse_done(msg.id, None)
        return

    yield _meta_event(cached=False, citations=references, conversation_id=conv.id)
    messages = [
        SystemMessage(content=prompt.SYSTEM_PROMPT_RAG),
        HumanMessage(content=prompt.build_user_prompt(references, history_text, question)),
    ]
    async for event in _stream_llm(db, conv, messages, references, cache_key):
        yield event


def _sse_error(detail: str) -> dict:
    return {"event": "error", "data": {"detail": detail}}


def _sse_done(message_id: int, token_count: int | None) -> dict:
    return {"event": "done", "data": {"message_id": message_id, "token_count": token_count}}
