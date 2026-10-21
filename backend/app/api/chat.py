"""SSE 流式问答端点。

事件协议（前端用 fetch + ReadableStream 消费）：
  meta（会话/引用信息，先于答案到达）→ 多个 delta → done / error
"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.database import SessionLocal
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(body: ChatRequest, user: User = Depends(get_current_user)):
    """流式问答。任何异常都转成 error 事件，绝不让流中断成 500。"""

    async def event_stream():
        # 流式响应期间依赖注入的会话已关闭，这里单独开一个数据库会话
        db = SessionLocal()
        try:
            async for event in chat_service.stream_chat(
                db, user, body.conversation_id, body.message
            ):
                yield _sse(event["event"], event["data"])
        except chat_service.ConversationNotFoundError as e:
            yield _sse("error", {"detail": str(e)})
        except Exception:  # noqa: BLE001
            logger.exception("聊天流式生成失败")
            yield _sse("error", {"detail": "系统繁忙，请稍后重试"})
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防止反向代理缓冲 SSE 流
        },
    )
