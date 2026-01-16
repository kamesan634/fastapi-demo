"""
使用者管理 API 端點

提供使用者的 CRUD 操作。

端點：
- GET /: 取得使用者列表
- POST /: 建立使用者
- GET /{user_id}: 取得單一使用者
- PUT /{user_id}: 更新使用者
- DELETE /{user_id}: 刪除使用者
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep, require_role
from app.kamesan.core.security import get_password_hash
from app.kamesan.models.user import Role, User
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse], summary="取得使用者列表")
async def get_users(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁筆數"),
    search: Optional[str] = Query(default=None, description="搜尋關鍵字"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
):
    """
    取得使用者列表

    支援分頁、搜尋和篩選。

    參數：
    - page: 頁碼
    - page_size: 每頁筆數
    - search: 搜尋關鍵字（帳號、姓名、Email）
    - is_active: 是否啟用

    回傳：
    - items: 使用者列表
    - total: 總筆數
    - page: 當前頁碼
    - page_size: 每頁筆數
    - pages: 總頁數
    """
    # 建立基本查詢
    statement = select(User).options(selectinload(User.role))

    # 排除已刪除的使用者
    statement = statement.where(User.is_deleted == False)

    # 搜尋條件
    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (User.username.ilike(search_pattern))
            | (User.full_name.ilike(search_pattern))
            | (User.email.ilike(search_pattern))
        )

    # 篩選條件
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)

    # 計算總筆數
    count_statement = select(User).where(User.is_deleted == False)
    if search:
        count_statement = count_statement.where(
            (User.username.ilike(search_pattern))
            | (User.full_name.ilike(search_pattern))
            | (User.email.ilike(search_pattern))
        )
    if is_active is not None:
        count_statement = count_statement.where(User.is_active == is_active)

    count_result = await session.execute(count_statement)
    total = len(count_result.all())

    # 分頁
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size)
    statement = statement.order_by(User.id.desc())

    # 執行查詢
    result = await session.execute(statement)
    users = result.scalars().all()

    return PaginatedResponse.create(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="建立使用者")
async def create_user(
    user_data: UserCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立使用者

    建立新的系統使用者。

    參數：
    - username: 帳號
    - email: 電子郵件
    - password: 密碼
    - full_name: 姓名
    - phone: 電話
    - is_active: 是否啟用
    - role_id: 角色 ID
    - store_id: 所屬門市 ID

    回傳：
    - 新建立的使用者資訊
    """
    # 檢查帳號是否已存在
    statement = select(User).where(User.username == user_data.username)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="帳號已存在",
        )

    # 檢查 Email 是否已存在
    statement = select(User).where(User.email == user_data.email)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email 已存在",
        )

    # 驗證角色是否存在
    if user_data.role_id:
        statement = select(Role).where(Role.id == user_data.role_id)
        result = await session.execute(statement)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色不存在",
            )

    # 建立使用者
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=user_data.is_active,
        role_id=user_data.role_id,
        store_id=user_data.store_id,
        created_by=current_user.id,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # 重新查詢以載入關聯資料
    statement = select(User).options(selectinload(User.role)).where(User.id == user.id)
    result = await session.execute(statement)
    user = result.scalar_one()

    return user


@router.get("/{user_id}", response_model=UserResponse, summary="取得單一使用者")
async def get_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得單一使用者

    根據 ID 取得使用者詳細資訊。

    參數：
    - user_id: 使用者 ID

    回傳：
    - 使用者資訊
    """
    statement = (
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id, User.is_deleted == False)
    )
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在",
        )

    return user


@router.put("/{user_id}", response_model=UserResponse, summary="更新使用者")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    更新使用者

    更新使用者資訊。

    參數：
    - user_id: 使用者 ID
    - user_data: 要更新的資料

    回傳：
    - 更新後的使用者資訊
    """
    # 查詢使用者
    statement = select(User).where(User.id == user_id, User.is_deleted == False)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在",
        )

    # 更新資料
    update_data = user_data.model_dump(exclude_unset=True)

    # 檢查帳號是否重複
    if "username" in update_data and update_data["username"] != user.username:
        statement = select(User).where(User.username == update_data["username"])
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="帳號已存在",
            )

    # 檢查 Email 是否重複
    if "email" in update_data and update_data["email"] != user.email:
        statement = select(User).where(User.email == update_data["email"])
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email 已存在",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_by = current_user.id
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # 重新查詢以載入關聯資料
    statement = select(User).options(selectinload(User.role)).where(User.id == user.id)
    result = await session.execute(statement)
    user = result.scalar_one()

    return user


@router.delete("/{user_id}", response_model=UserResponse, summary="刪除使用者")
async def delete_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    刪除使用者

    軟刪除使用者（標記為已刪除）。

    參數：
    - user_id: 使用者 ID

    回傳：
    - 被刪除的使用者資訊
    """
    # 不能刪除自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能刪除自己的帳號",
        )

    # 查詢使用者
    statement = select(User).where(User.id == user_id, User.is_deleted == False)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在",
        )

    # 執行軟刪除
    user.soft_delete()
    user.updated_by = current_user.id
    session.add(user)
    await session.commit()

    return user
