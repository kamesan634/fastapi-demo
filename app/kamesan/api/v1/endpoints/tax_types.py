"""
稅別管理 API 端點

提供稅別的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import TaxType
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.product import TaxTypeCreate, TaxTypeResponse, TaxTypeUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TaxTypeResponse], summary="取得稅別列表")
async def get_tax_types(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
):
    """取得稅別列表"""
    statement = select(TaxType)

    if is_active is not None:
        statement = statement.where(TaxType.is_active == is_active)

    count_result = await session.execute(select(TaxType))
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(TaxType.id)

    result = await session.execute(statement)
    tax_types = result.scalars().all()

    return PaginatedResponse.create(items=tax_types, total=total, page=page, page_size=page_size)


@router.post("", response_model=TaxTypeResponse, status_code=status.HTTP_201_CREATED, summary="建立稅別")
async def create_tax_type(
    tax_type_data: TaxTypeCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立稅別"""
    statement = select(TaxType).where(TaxType.code == tax_type_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="稅別代碼已存在")

    tax_type = TaxType(**tax_type_data.model_dump())
    session.add(tax_type)
    await session.commit()
    await session.refresh(tax_type)

    return tax_type


@router.get("/{tax_type_id}", response_model=TaxTypeResponse, summary="取得單一稅別")
async def get_tax_type(tax_type_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一稅別"""
    statement = select(TaxType).where(TaxType.id == tax_type_id)
    result = await session.execute(statement)
    tax_type = result.scalar_one_or_none()

    if tax_type is None:
        raise HTTPException(status_code=404, detail="稅別不存在")

    return tax_type


@router.put("/{tax_type_id}", response_model=TaxTypeResponse, summary="更新稅別")
async def update_tax_type(
    tax_type_id: int,
    tax_type_data: TaxTypeUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新稅別"""
    statement = select(TaxType).where(TaxType.id == tax_type_id)
    result = await session.execute(statement)
    tax_type = result.scalar_one_or_none()

    if tax_type is None:
        raise HTTPException(status_code=404, detail="稅別不存在")

    update_data = tax_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tax_type, field, value)

    session.add(tax_type)
    await session.commit()
    await session.refresh(tax_type)

    return tax_type


@router.delete("/{tax_type_id}", response_model=TaxTypeResponse, summary="刪除稅別")
async def delete_tax_type(tax_type_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除稅別"""
    statement = select(TaxType).where(TaxType.id == tax_type_id)
    result = await session.execute(statement)
    tax_type = result.scalar_one_or_none()

    if tax_type is None:
        raise HTTPException(status_code=404, detail="稅別不存在")

    await session.delete(tax_type)
    await session.commit()

    return tax_type
