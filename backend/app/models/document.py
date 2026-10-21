"""文档表：知识库中上传的原始文档及其入库状态。"""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # 原始文件名（展示用）
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)  # uuid 命名防路径穿越
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf/docx/xlsx/txt/md
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # 状态机：pending → processing → success / failed（前端轮询此字段）
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
