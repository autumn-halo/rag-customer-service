"""安全组件单元测试：密码哈希与 JWT。"""
import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_plaintext():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gets_different_hash():
    # bcrypt 加盐：同样的密码两次哈希结果不同，防止彩虹表攻击
    assert hash_password("secret123") != hash_password("secret123")


def test_jwt_roundtrip():
    token = create_access_token(42, "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_jwt_tampered_token_rejected():
    token = create_access_token(1, "user")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "tampered")
