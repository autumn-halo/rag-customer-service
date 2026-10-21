"""用户相关接口的请求/响应数据结构。"""
from pydantic import BaseModel, ConfigDict, Field

# 用户名：3-20 位，允许中英文、数字、下划线和连字符
USERNAME_PATTERN = r"^[\w一-龥-]+$"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=6, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)
