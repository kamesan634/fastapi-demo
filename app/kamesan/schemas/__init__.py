"""
Pydantic 模型模組

定義 API 請求和回應的資料模型。

結構：
- auth: 認證相關模型
- user: 使用者相關模型
- common: 共用模型（分頁、回應等）
- 其他模組依據功能分類
"""

from app.kamesan.schemas.auth import Token, TokenPayload, LoginRequest, RefreshTokenRequest
from app.kamesan.schemas.common import PaginatedResponse, MessageResponse
from app.kamesan.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
)

__all__ = [
    # 認證
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshTokenRequest",
    # 共用
    "PaginatedResponse",
    "MessageResponse",
    # 使用者
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
]
