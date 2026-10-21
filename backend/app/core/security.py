"""安全组件：密码哈希（bcrypt）与登录令牌（JWT）的签发/解析。"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """把明文密码变成不可逆的哈希串，数据库里绝不存明文。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与存储的哈希是否匹配。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    """签发登录令牌，内含用户 id、角色和过期时间。"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析并校验令牌；无效、被篡改或过期时抛 jwt.PyJWTError。"""
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
