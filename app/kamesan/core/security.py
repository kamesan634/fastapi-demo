"""
安全性模組

提供 JWT Token 產生與驗證、密碼雜湊等安全性功能。

功能：
- JWT Access Token 產生與驗證
- JWT Refresh Token 產生與驗證
- 密碼雜湊與驗證
- Token 黑名單管理（使用 Redis）
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.kamesan.core.config import settings

# ==========================================
# 密碼雜湊設定
# ==========================================
# 使用 bcrypt 演算法進行密碼雜湊
# deprecated="auto" 表示自動處理舊版演算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼

    比對使用者輸入的明文密碼與資料庫中的雜湊密碼。

    參數:
        plain_password: 使用者輸入的明文密碼
        hashed_password: 資料庫中儲存的雜湊密碼

    回傳值:
        bool: 密碼是否正確
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    產生密碼雜湊

    使用 bcrypt 演算法將明文密碼轉換為雜湊值。

    參數:
        password: 明文密碼

    回傳值:
        str: 雜湊後的密碼
    """
    return pwd_context.hash(password)


# ==========================================
# JWT Token 功能
# ==========================================
def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    建立 Access Token

    產生用於 API 認證的 JWT Token。

    參數:
        subject: Token 主體（通常是使用者 ID）
        expires_delta: Token 有效期限，預設使用設定檔中的值
        additional_claims: 額外的 JWT claims

    回傳值:
        str: 編碼後的 JWT Token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    建立 Refresh Token

    產生用於更新 Access Token 的 JWT Token。
    Refresh Token 有效期較長，用於在 Access Token 過期後取得新的 Token。

    參數:
        subject: Token 主體（通常是使用者 ID）
        expires_delta: Token 有效期限，預設使用設定檔中的值

    回傳值:
        str: 編碼後的 JWT Refresh Token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    解碼 JWT Token

    驗證並解碼 JWT Token，取得其中的 payload。

    參數:
        token: 要解碼的 JWT Token

    回傳值:
        Optional[dict]: 解碼後的 payload，驗證失敗則回傳 None
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    驗證 Token 並取得使用者 ID

    驗證 JWT Token 的有效性，並確認 Token 類型正確。

    參數:
        token: 要驗證的 JWT Token
        token_type: Token 類型（"access" 或 "refresh"）

    回傳值:
        Optional[str]: 使用者 ID，驗證失敗則回傳 None
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # 檢查 Token 類型
    if payload.get("type") != token_type:
        return None

    # 取得使用者 ID
    user_id: str = payload.get("sub")
    if user_id is None:
        return None

    return user_id
