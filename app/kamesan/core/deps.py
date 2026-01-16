"""
依賴注入模組

提供 FastAPI 依賴注入所需的各種依賴函數。

功能：
- 資料庫 Session 依賴
- 當前使用者依賴
- 權限檢查依賴
- Redis 連線依賴
"""

from typing import Annotated, Optional

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.config import settings
from app.kamesan.core.database import get_async_session
from app.kamesan.core.security import verify_token

# ==========================================
# OAuth2 設定
# ==========================================
# 定義 Token 取得的 URL 端點
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,  # 允許未認證的請求通過（由依賴函數處理）
)

# ==========================================
# 類型別名
# ==========================================
# 使用 Annotated 簡化依賴注入的類型標註
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[Optional[str], Depends(oauth2_scheme)]


# ==========================================
# Redis 連線依賴
# ==========================================
# Redis 連線池（全域變數，應用程式啟動時初始化）
redis_pool: Optional[redis.ConnectionPool] = None


async def get_redis() -> redis.Redis:
    """
    取得 Redis 連線

    從連線池取得 Redis 連線實例。

    回傳值:
        redis.Redis: Redis 連線實例

    異常:
        HTTPException: 當 Redis 連線池未初始化時
    """
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return redis.Redis(connection_pool=redis_pool)


RedisDep = Annotated[redis.Redis, Depends(get_redis)]


# ==========================================
# 使用者認證依賴
# ==========================================
async def get_current_user(
    session: SessionDep,
    token: TokenDep,
):
    """
    取得當前登入使用者

    驗證 JWT Token 並從資料庫取得使用者資訊。

    參數:
        session: 資料庫 Session
        token: JWT Token（從 Authorization header 取得）

    回傳值:
        User: 當前登入的使用者物件

    異常:
        HTTPException 401: Token 無效或使用者不存在
        HTTPException 403: 使用者帳號已停用
    """
    # 延遲匯入避免循環依賴
    from app.kamesan.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    # 驗證 Token
    user_id = verify_token(token, token_type="access")
    if user_id is None:
        raise credentials_exception

    # 從資料庫取得使用者（eager load role 關聯）
    statement = select(User).where(User.id == int(user_id)).options(selectinload(User.role))
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # 檢查使用者狀態
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號已停用",
        )

    return user


async def get_current_user_optional(
    session: SessionDep,
    token: TokenDep,
):
    """
    取得當前登入使用者（可選）

    與 get_current_user 類似，但允許未認證的請求。
    用於某些端點需要區分已登入/未登入使用者的情況。

    參數:
        session: 資料庫 Session
        token: JWT Token（從 Authorization header 取得）

    回傳值:
        Optional[User]: 當前登入的使用者物件，未認證則回傳 None
    """
    if token is None:
        return None

    try:
        return await get_current_user(session, token)
    except HTTPException:
        return None


# ==========================================
# 權限檢查依賴工廠
# ==========================================
def require_permissions(*permissions: str):
    """
    權限檢查依賴工廠

    建立一個依賴函數，檢查使用者是否具有指定的權限。

    參數:
        *permissions: 需要的權限代碼列表

    回傳值:
        依賴函數，回傳當前使用者（已驗證權限）

    使用範例:
        @router.get("/admin")
        async def admin_only(
            user = Depends(require_permissions("admin.access"))
        ):
            ...
    """

    async def permission_checker(
        session: SessionDep,
        token: TokenDep,
    ):
        # 延遲匯入避免循環依賴
        from app.kamesan.models.user import User

        user = await get_current_user(session, token)

        # 超級管理員擁有所有權限
        if user.is_superuser:
            return user

        # 檢查使用者角色的權限
        # 這裡需要根據實際的權限模型調整
        user_permissions = set()
        if user.role:
            # 假設 Role 有 permissions 欄位存放權限列表
            if hasattr(user.role, "permissions") and user.role.permissions:
                user_permissions = set(user.role.permissions.split(","))

        # 檢查是否具有所有要求的權限
        required_permissions = set(permissions)
        if not required_permissions.issubset(user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="權限不足",
            )

        return user

    return permission_checker


def require_role(*role_codes: str):
    """
    角色檢查依賴工廠

    建立一個依賴函數，檢查使用者是否具有指定的角色。

    參數:
        *role_codes: 允許的角色代碼列表

    回傳值:
        依賴函數，回傳當前使用者（已驗證角色）

    使用範例:
        @router.get("/managers")
        async def managers_only(
            user = Depends(require_role("ADMIN", "MANAGER"))
        ):
            ...
    """

    async def role_checker(
        session: SessionDep,
        token: TokenDep,
    ):
        user = await get_current_user(session, token)

        # 超級管理員通過所有角色檢查
        if user.is_superuser:
            return user

        # 檢查使用者角色
        if user.role is None or user.role.code not in role_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="角色權限不足",
            )

        return user

    return role_checker


# ==========================================
# 常用依賴類型別名
# ==========================================
# 當前使用者依賴（必須登入）
CurrentUser = Annotated[object, Depends(get_current_user)]

# 當前使用者依賴（可選登入）
OptionalUser = Annotated[Optional[object], Depends(get_current_user_optional)]
