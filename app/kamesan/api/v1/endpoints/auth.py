"""
認證 API 端點

提供使用者登入、登出、Token 刷新等功能。

端點：
- POST /login: 使用者登入
- POST /logout: 使用者登出
- POST /refresh: 刷新 Token
- GET /me: 取得當前使用者資訊
- POST /change-password: 變更密碼
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.kamesan.core.database import get_async_session
from app.kamesan.core.deps import CurrentUser, RedisDep, SessionDep
from app.kamesan.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.kamesan.models.user import User
from app.kamesan.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    Token,
)
from app.kamesan.schemas.common import MessageResponse
from app.kamesan.schemas.user import UserResponse

router = APIRouter()


@router.post("/login", response_model=Token, summary="使用者登入")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: SessionDep = None,
):
    """
    使用者登入

    使用帳號密碼進行登入，成功後回傳 JWT Token。

    參數：
    - username: 帳號
    - password: 密碼

    回傳：
    - access_token: Access Token
    - refresh_token: Refresh Token
    - token_type: Token 類型
    """
    # 查詢使用者
    statement = select(User).where(User.username == form_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    # 驗證使用者
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查使用者狀態
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號已停用",
        )

    # 更新最後登入時間
    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()

    # 產生 Token
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login-json", response_model=Token, summary="使用者登入（JSON）")
async def login_json(
    login_data: LoginRequest,
    session: SessionDep = None,
):
    """
    使用者登入（JSON 格式）

    使用 JSON 格式的帳號密碼進行登入。

    參數：
    - username: 帳號
    - password: 密碼

    回傳：
    - access_token: Access Token
    - refresh_token: Refresh Token
    - token_type: Token 類型
    """
    # 查詢使用者
    statement = select(User).where(User.username == login_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    # 驗證使用者
    if user is None or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查使用者狀態
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號已停用",
        )

    # 更新最後登入時間
    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()

    # 產生 Token
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token, summary="刷新 Token")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: SessionDep = None,
):
    """
    刷新 Token

    使用 Refresh Token 取得新的 Access Token。

    參數：
    - refresh_token: Refresh Token

    回傳：
    - access_token: 新的 Access Token
    - refresh_token: 新的 Refresh Token
    - token_type: Token 類型
    """
    # 驗證 Refresh Token
    user_id = verify_token(refresh_data.refresh_token, token_type="refresh")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Refresh Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查詢使用者
    statement = select(User).where(User.id == int(user_id))
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="使用者不存在或已停用",
        )

    # 產生新的 Token
    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post("/logout", response_model=MessageResponse, summary="使用者登出")
async def logout(
    current_user: CurrentUser,
    redis: RedisDep,
):
    """
    使用者登出

    將當前 Token 加入黑名單（需要 Redis）。

    回傳：
    - message: 登出成功訊息
    """
    # 這裡可以將 Token 加入 Redis 黑名單
    # 目前簡化處理，僅回傳成功訊息
    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserResponse, summary="取得當前使用者資訊")
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    取得當前使用者資訊

    回傳當前登入使用者的詳細資訊。

    回傳：
    - 使用者資訊
    """
    return current_user


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="變更密碼",
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    """
    變更密碼

    變更當前使用者的密碼。

    參數：
    - current_password: 目前密碼
    - new_password: 新密碼
    - new_password_confirm: 確認新密碼

    回傳：
    - message: 變更成功訊息
    """
    # 驗證目前密碼
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目前密碼錯誤",
        )

    # 驗證新密碼確認
    if password_data.new_password != password_data.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密碼與確認密碼不符",
        )

    # 更新密碼
    current_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(current_user)
    await session.commit()

    return MessageResponse(message="密碼變更成功")
