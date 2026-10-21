"""会话表：每个用户拥有多个独立会话。"""
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        # 会话列表按"用户 + 最近更新时间"倒序查询
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="新会话")

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
