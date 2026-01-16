"""
倉庫管理 API 端點

提供倉庫的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.store import Warehouse
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.store import WarehouseCreate, WarehouseResponse, WarehouseUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[WarehouseResponse], summary="取得倉庫列表")
async def get_warehouses(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """取得倉庫列表"""
    statement = select(Warehouse).where(Warehouse.is_deleted == False)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Warehouse.code.ilike(search_pattern)) | (Warehouse.name.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Warehouse.is_active == is_active)

    count_result = await session.execute(
        select(Warehouse).where(Warehouse.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Warehouse.id.desc())

    result = await session.execute(statement)
    warehouses = result.scalars().all()

    return PaginatedResponse.create(items=warehouses, total=total, page=page, page_size=page_size)


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED, summary="建立倉庫")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立倉庫"""
    statement = select(Warehouse).where(Warehouse.code == warehouse_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="倉庫代碼已存在")

    warehouse = Warehouse(**warehouse_data.model_dump(), created_by=current_user.id)
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)

    return warehouse


@router.get("/{warehouse_id}", response_model=WarehouseResponse, summary="取得單一倉庫")
async def get_warehouse(warehouse_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一倉庫"""
    statement = select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_deleted == False)
    result = await session.execute(statement)
    warehouse = result.scalar_one_or_none()

    if warehouse is None:
        raise HTTPException(status_code=404, detail="倉庫不存在")

    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse, summary="更新倉庫")
async def update_warehouse(
    warehouse_id: int,
    warehouse_data: WarehouseUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新倉庫"""
    statement = select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_deleted == False)
    result = await session.execute(statement)
    warehouse = result.scalar_one_or_none()

    if warehouse is None:
        raise HTTPException(status_code=404, detail="倉庫不存在")

    update_data = warehouse_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(warehouse, field, value)

    warehouse.updated_by = current_user.id
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)

    return warehouse


@router.delete("/{warehouse_id}", response_model=WarehouseResponse, summary="刪除倉庫")
async def delete_warehouse(warehouse_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除倉庫"""
    statement = select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_deleted == False)
    result = await session.execute(statement)
    warehouse = result.scalar_one_or_none()

    if warehouse is None:
        raise HTTPException(status_code=404, detail="倉庫不存在")

    warehouse.soft_delete()
    warehouse.updated_by = current_user.id
    session.add(warehouse)
    await session.commit()

    return warehouse
