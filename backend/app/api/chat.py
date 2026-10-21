"""SSE 流式问答端点。

事件协议（前端用 fetch + ReadableStream 消费）：
  meta（会话/引用信息，先于答案到达）→ 多个 delta → done / error
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.database import SessionLocal
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# 每个用户每分钟最多 N 次提问（防刷接口）
_chat_limiter = SlidingWindowRateLimiter(settings.rate_limit_chat_per_min)


def check_chat_rate(user: User = Depends(get_current_user)) -> User:
    if not _chat_limiter.allow(f"user:{user.id}"):
        raise HTTPException(status_code=429, detail="提问太频繁了，请稍后再试")
    return user


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _with_heartbeat(agen, interval: float = 15.0):
    """流式输出期间每 interval 秒发一次 SSE 心跳注释。

    模型长时间思考时没有数据产出，浏览器/代理可能判定连接超时断连；
    心跳注释（SSE 协议规定注释行会被客户端忽略）保活连接。
    """
    it = agen.__aiter__()
    while True:
        try:
            event = await asyncio.wait_for(it.__anext__(), timeout=interval)
        except asyncio.TimeoutError:
            yield ": ping\n\n"
        except StopAsyncIteration:
            return
        else:
            yield _sse(event["event"], event["data"])


@router.post("/stream")
async def chat_stream(body: ChatRequest, user: User = Depends(check_chat_rate)):
    """流式问答。任何异常都转成 error 事件，绝不让流中断成 500。"""

    async def event_stream():
        # 流式响应期间依赖注入的会话已关闭，这里单独开一个数据库会话
        db = SessionLocal()
        try:
            async for frame in _with_heartbeat(
                chat_service.stream_chat(db, user, body.conversation_id, body.message)
            ):
                yield frame
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
