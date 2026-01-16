"""
供應商管理 API 端點

提供供應商的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SupplierResponse], summary="取得供應商列表")
async def get_suppliers(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """取得供應商列表"""
    statement = select(Supplier).where(Supplier.is_deleted == False)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Supplier.code.ilike(search_pattern)) | (Supplier.name.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Supplier.is_active == is_active)

    count_result = await session.execute(
        select(Supplier).where(Supplier.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Supplier.id.desc())

    result = await session.execute(statement)
    suppliers = result.scalars().all()

    return PaginatedResponse.create(items=suppliers, total=total, page=page, page_size=page_size)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, summary="建立供應商")
async def create_supplier(
    supplier_data: SupplierCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立供應商"""
    statement = select(Supplier).where(Supplier.code == supplier_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="供應商代碼已存在")

    supplier = Supplier(**supplier_data.model_dump(), created_by=current_user.id)
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)

    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse, summary="取得單一供應商")
async def get_supplier(supplier_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一供應商"""
    statement = select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    result = await session.execute(statement)
    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(status_code=404, detail="供應商不存在")

    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse, summary="更新供應商")
async def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新供應商"""
    statement = select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    result = await session.execute(statement)
    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(status_code=404, detail="供應商不存在")

    update_data = supplier_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    supplier.updated_by = current_user.id
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)

    return supplier


@router.delete("/{supplier_id}", response_model=SupplierResponse, summary="刪除供應商")
async def delete_supplier(supplier_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除供應商"""
    statement = select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    result = await session.execute(statement)
    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(status_code=404, detail="供應商不存在")

    supplier.soft_delete()
    supplier.updated_by = current_user.id
    session.add(supplier)
    await session.commit()

    return supplier
