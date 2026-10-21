"""聊天编排：会话创建、历史加载、模型流式回答、消息落库。

阶段 3 为纯对话骨架；阶段 4 接入 RAG 检索后，本模块在生成答案前
先检索知识库并把引用片段注入 prompt。
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.base import utcnow
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.rag.chain import get_chat_model

SYSTEM_PROMPT = "你是「XX商城」的智能客服助手，请用简体中文亲切、专业地回答用户问题。"


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


def _history_to_messages(history: list[dict]) -> list:
    return [
        HumanMessage(content=m["content"])
        if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in history
    ]


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

    yield {
        "event": "meta",
        "data": {"cached": False, "citations": [], "conversation_id": conv.id},
    }

    # 2. 组装提示词：系统设定 + 最近几轮历史 + 当前问题
    history = _load_history(db, conv.id, settings.history_turns)
    messages = [SystemMessage(content=SYSTEM_PROMPT), *_history_to_messages(history)]
    messages.append(HumanMessage(content=question))

    # 3. 流式生成答案
    llm = get_chat_model()
    full_text = ""
    token_count = None
    async for chunk in llm.astream(messages):
        text = chunk.content or ""
        full_text += text
        yield {"event": "delta", "data": {"content": text}}
        usage = getattr(chunk, "usage_metadata", None)
        if usage:
            token_count = usage.get("total_tokens")

    # 4. 保存助手消息（含 token 用量）
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=full_text,
        token_count=token_count,
    )
    db.add(assistant_msg)
    conv.updated_at = utcnow()
    db.commit()
    db.refresh(assistant_msg)

    yield {"event": "done", "data": {"message_id": assistant_msg.id, "token_count": token_count}}
