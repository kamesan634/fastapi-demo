"""
認證相關 Schema 模型

定義認證相關的請求和回應模型。

模型：
- LoginRequest: 登入請求
- Token: Token 回應
- TokenPayload: Token 內容
- RefreshTokenRequest: Token 刷新請求
"""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """
    登入請求模型

    屬性：
    - username: 帳號
    - password: 密碼
    """

    username: str = Field(min_length=1, max_length=50, description="帳號")
    password: str = Field(min_length=1, max_length=128, description="密碼")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "admin",
                    "password": "admin123",
                }
            ]
        }
    }


class Token(BaseModel):
    """
    Token 回應模型

    屬性：
    - access_token: Access Token
    - refresh_token: Refresh Token
    - token_type: Token 類型
    """

    access_token: str = Field(description="Access Token")
    refresh_token: str = Field(description="Refresh Token")
    token_type: str = Field(default="bearer", description="Token 類型")


class TokenPayload(BaseModel):
    """
    Token 內容模型

    JWT Token 解碼後的內容。

    屬性：
    - sub: 主體（使用者 ID）
    - exp: 過期時間
    - type: Token 類型
    """

    sub: str = Field(description="主體（使用者 ID）")
    exp: int = Field(description="過期時間戳")
    type: str = Field(description="Token 類型")


class RefreshTokenRequest(BaseModel):
    """
    Token 刷新請求模型

    屬性：
    - refresh_token: Refresh Token
    """

    refresh_token: str = Field(description="Refresh Token")


class ChangePasswordRequest(BaseModel):
    """
    變更密碼請求模型

    屬性：
    - current_password: 目前密碼
    - new_password: 新密碼
    - new_password_confirm: 確認新密碼
    """

    current_password: str = Field(min_length=1, description="目前密碼")
    new_password: str = Field(min_length=6, max_length=128, description="新密碼")
    new_password_confirm: str = Field(min_length=6, max_length=128, description="確認新密碼")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_password": "old_password",
                    "new_password": "new_password123",
                    "new_password_confirm": "new_password123",
                }
            ]
        }
    }
