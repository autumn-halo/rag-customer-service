"""汇总导入所有 ORM 模型，保证 Base.metadata 完整建表。"""
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.user import User  # noqa: F401
