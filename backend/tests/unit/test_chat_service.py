"""chat_service 内部逻辑单元测试：会话创建、历史截断。"""
from app.database import SessionLocal
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services import chat_service


def _make_user(username: str = "alice") -> User:
    with SessionLocal() as db:
        user = User(username=username, password_hash="x", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def test_title_truncated_to_20_chars():
    user = _make_user()
    long_q = "请问你们店铺的退换货政策具体是怎么规定的呀？"
    with SessionLocal() as db:
        conv = chat_service._get_or_create_conversation(db, user, None, long_q)
        assert conv.title == long_q[:20]
        assert len(conv.title) == 20


def test_blank_question_gets_default_title():
    user = _make_user()
    with SessionLocal() as db:
        conv = chat_service._get_or_create_conversation(db, user, None, "   ")
        assert conv.title == "新会话"


def test_missing_conversation_raises():
    user = _make_user()
    with SessionLocal() as db:
        try:
            chat_service._get_or_create_conversation(db, user, 99999, "你好")
            raise AssertionError("应当抛出 ConversationNotFoundError")
        except chat_service.ConversationNotFoundError:
            pass


def test_others_conversation_raises():
    alice = _make_user("alice")
    bob = _make_user("bob")
    with SessionLocal() as db:
        conv = chat_service._get_or_create_conversation(db, alice, None, "问题")
        try:
            chat_service._get_or_create_conversation(db, bob, conv.id, "问题")
            raise AssertionError("应当抛出 ConversationNotFoundError")
        except chat_service.ConversationNotFoundError:
            pass


def test_load_history_limits_turns_and_orders_chronologically():
    user = _make_user()
    with SessionLocal() as db:
        conv = Conversation(user_id=user.id, title="t")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            db.add(Message(conversation_id=conv.id, role=role, content=f"消息{i}"))
        db.commit()

        # turns=2 → 只取最近 4 条（2 问 2 答），且按时间正序返回
        history = chat_service._load_history(db, conv.id, turns=2)
        assert [m["content"] for m in history] == ["消息6", "消息7", "消息8", "消息9"]
