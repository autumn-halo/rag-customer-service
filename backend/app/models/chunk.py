"""分块表：文档切分后的知识片段（chunks 表是检索数据的"事实来源"）。"""
from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 文档内顺序
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 注意：列名用 "metadata"、属性名用 meta，避免与 SQLAlchemy 的 metadata 冲突
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)  # 页码/sheet 名等
    chroma_id: Mapped[str] = mapped_column(String(64), nullable=False)  # 向量库中的 ID

    document = relationship("Document", back_populates="chunks")
