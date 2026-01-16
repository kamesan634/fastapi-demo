"""
客戶等級管理 API 端點

提供客戶等級的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.customer import CustomerLevel
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.customer import CustomerLevelCreate, CustomerLevelResponse, CustomerLevelUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CustomerLevelResponse], summary="取得客戶等級列表")
async def get_customer_levels(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
):
    """取得客戶等級列表"""
    statement = select(CustomerLevel)

    if is_active is not None:
        statement = statement.where(CustomerLevel.is_active == is_active)

    count_result = await session.execute(select(CustomerLevel))
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(CustomerLevel.min_spending)

    result = await session.execute(statement)
    levels = result.scalars().all()

    return PaginatedResponse.create(items=levels, total=total, page=page, page_size=page_size)


@router.post("", response_model=CustomerLevelResponse, status_code=status.HTTP_201_CREATED, summary="建立客戶等級")
async def create_customer_level(
    level_data: CustomerLevelCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立客戶等級"""
    statement = select(CustomerLevel).where(CustomerLevel.code == level_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="等級代碼已存在")

    level = CustomerLevel(**level_data.model_dump())
    session.add(level)
    await session.commit()
    await session.refresh(level)

    return level


@router.get("/{level_id}", response_model=CustomerLevelResponse, summary="取得單一客戶等級")
async def get_customer_level(level_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一客戶等級"""
    statement = select(CustomerLevel).where(CustomerLevel.id == level_id)
    result = await session.execute(statement)
    level = result.scalar_one_or_none()

    if level is None:
        raise HTTPException(status_code=404, detail="客戶等級不存在")

    return level


@router.put("/{level_id}", response_model=CustomerLevelResponse, summary="更新客戶等級")
async def update_customer_level(
    level_id: int,
    level_data: CustomerLevelUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新客戶等級"""
    statement = select(CustomerLevel).where(CustomerLevel.id == level_id)
    result = await session.execute(statement)
    level = result.scalar_one_or_none()

    if level is None:
        raise HTTPException(status_code=404, detail="客戶等級不存在")

    update_data = level_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(level, field, value)

    session.add(level)
    await session.commit()
    await session.refresh(level)

    return level


@router.delete("/{level_id}", response_model=CustomerLevelResponse, summary="刪除客戶等級")
async def delete_customer_level(level_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除客戶等級"""
    statement = select(CustomerLevel).where(CustomerLevel.id == level_id)
    result = await session.execute(statement)
    level = result.scalar_one_or_none()

    if level is None:
        raise HTTPException(status_code=404, detail="客戶等級不存在")

    await session.delete(level)
    await session.commit()

    return level
