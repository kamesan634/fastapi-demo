"""
單位管理 API 端點

提供單位的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Unit
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.product import UnitCreate, UnitResponse, UnitUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UnitResponse], summary="取得單位列表")
async def get_units(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
):
    """取得單位列表"""
    statement = select(Unit)

    if is_active is not None:
        statement = statement.where(Unit.is_active == is_active)

    count_result = await session.execute(select(Unit))
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Unit.id)

    result = await session.execute(statement)
    units = result.scalars().all()

    return PaginatedResponse.create(items=units, total=total, page=page, page_size=page_size)


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED, summary="建立單位")
async def create_unit(
    unit_data: UnitCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立單位"""
    statement = select(Unit).where(Unit.code == unit_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="單位代碼已存在")

    unit = Unit(**unit_data.model_dump())
    session.add(unit)
    await session.commit()
    await session.refresh(unit)

    return unit


@router.get("/{unit_id}", response_model=UnitResponse, summary="取得單一單位")
async def get_unit(unit_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一單位"""
    statement = select(Unit).where(Unit.id == unit_id)
    result = await session.execute(statement)
    unit = result.scalar_one_or_none()

    if unit is None:
        raise HTTPException(status_code=404, detail="單位不存在")

    return unit


@router.put("/{unit_id}", response_model=UnitResponse, summary="更新單位")
async def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新單位"""
    statement = select(Unit).where(Unit.id == unit_id)
    result = await session.execute(statement)
    unit = result.scalar_one_or_none()

    if unit is None:
        raise HTTPException(status_code=404, detail="單位不存在")

    update_data = unit_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(unit, field, value)

    session.add(unit)
    await session.commit()
    await session.refresh(unit)

    return unit


@router.delete("/{unit_id}", response_model=UnitResponse, summary="刪除單位")
async def delete_unit(unit_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除單位"""
    statement = select(Unit).where(Unit.id == unit_id)
    result = await session.execute(statement)
    unit = result.scalar_one_or_none()

    if unit is None:
        raise HTTPException(status_code=404, detail="單位不存在")

    await session.delete(unit)
    await session.commit()

    return unit
