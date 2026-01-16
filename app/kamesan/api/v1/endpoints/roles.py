"""
角色管理 API 端點

提供角色的 CRUD 操作。

端點：
- GET /: 取得角色列表
- POST /: 建立角色
- GET /{role_id}: 取得單一角色
- PUT /{role_id}: 更新角色
- DELETE /{role_id}: 刪除角色
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.user import Role
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.user import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[RoleResponse], summary="取得角色列表")
async def get_roles(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁筆數"),
    search: Optional[str] = Query(default=None, description="搜尋關鍵字"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
):
    """
    取得角色列表

    支援分頁、搜尋和篩選。
    """
    # 建立基本查詢
    statement = select(Role)

    # 搜尋條件
    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Role.code.ilike(search_pattern)) | (Role.name.ilike(search_pattern))
        )

    # 篩選條件
    if is_active is not None:
        statement = statement.where(Role.is_active == is_active)

    # 計算總筆數
    count_result = await session.execute(statement)
    total = len(count_result.all())

    # 分頁
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size)
    statement = statement.order_by(Role.id.desc())

    # 執行查詢
    result = await session.execute(statement)
    roles = result.scalars().all()

    return PaginatedResponse.create(
        items=roles,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, summary="建立角色")
async def create_role(
    role_data: RoleCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立角色

    建立新的角色。
    """
    # 檢查代碼是否已存在
    statement = select(Role).where(Role.code == role_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色代碼已存在",
        )

    # 建立角色
    role = Role(**role_data.model_dump())
    session.add(role)
    await session.commit()
    await session.refresh(role)

    return role


@router.get("/{role_id}", response_model=RoleResponse, summary="取得單一角色")
async def get_role(
    role_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得單一角色

    根據 ID 取得角色詳細資訊。
    """
    statement = select(Role).where(Role.id == role_id)
    result = await session.execute(statement)
    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    return role


@router.put("/{role_id}", response_model=RoleResponse, summary="更新角色")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    更新角色

    更新角色資訊。
    """
    # 查詢角色
    statement = select(Role).where(Role.id == role_id)
    result = await session.execute(statement)
    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    # 更新資料
    update_data = role_data.model_dump(exclude_unset=True)

    # 檢查代碼是否重複
    if "code" in update_data and update_data["code"] != role.code:
        statement = select(Role).where(Role.code == update_data["code"])
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色代碼已存在",
            )

    for field, value in update_data.items():
        setattr(role, field, value)

    session.add(role)
    await session.commit()
    await session.refresh(role)

    return role


@router.delete("/{role_id}", response_model=RoleResponse, summary="刪除角色")
async def delete_role(
    role_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    刪除角色

    刪除角色（若有使用者使用此角色則無法刪除）。
    """
    # 查詢角色
    statement = select(Role).where(Role.id == role_id)
    result = await session.execute(statement)
    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    # 檢查是否有使用者使用此角色
    from app.kamesan.models.user import User

    statement = select(User).where(User.role_id == role_id, User.is_deleted == False)
    result = await session.execute(statement)
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此角色尚有使用者使用，無法刪除",
        )

    # 刪除角色
    await session.delete(role)
    await session.commit()

    return role
