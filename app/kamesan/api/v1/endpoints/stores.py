"""
門市管理 API 端點

提供門市的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.store import Store
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.store import StoreCreate, StoreResponse, StoreUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[StoreResponse], summary="取得門市列表")
async def get_stores(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """取得門市列表"""
    statement = select(Store).options(selectinload(Store.warehouse))
    statement = statement.where(Store.is_deleted == False)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Store.code.ilike(search_pattern)) | (Store.name.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Store.is_active == is_active)

    count_result = await session.execute(
        select(Store).where(Store.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Store.id.desc())

    result = await session.execute(statement)
    stores = result.scalars().all()

    return PaginatedResponse.create(items=stores, total=total, page=page, page_size=page_size)


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED, summary="建立門市")
async def create_store(
    store_data: StoreCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立門市"""
    statement = select(Store).where(Store.code == store_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="門市代碼已存在")

    store = Store(**store_data.model_dump(), created_by=current_user.id)
    session.add(store)
    await session.commit()
    await session.refresh(store)

    return store


@router.get("/{store_id}", response_model=StoreResponse, summary="取得單一門市")
async def get_store(store_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一門市"""
    statement = (
        select(Store)
        .options(selectinload(Store.warehouse))
        .where(Store.id == store_id, Store.is_deleted == False)
    )
    result = await session.execute(statement)
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(status_code=404, detail="門市不存在")

    return store


@router.put("/{store_id}", response_model=StoreResponse, summary="更新門市")
async def update_store(
    store_id: int,
    store_data: StoreUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新門市"""
    statement = select(Store).where(Store.id == store_id, Store.is_deleted == False)
    result = await session.execute(statement)
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(status_code=404, detail="門市不存在")

    update_data = store_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    store.updated_by = current_user.id
    session.add(store)
    await session.commit()
    await session.refresh(store)

    return store


@router.delete("/{store_id}", response_model=StoreResponse, summary="刪除門市")
async def delete_store(store_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除門市"""
    statement = select(Store).where(Store.id == store_id, Store.is_deleted == False)
    result = await session.execute(statement)
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(status_code=404, detail="門市不存在")

    store.soft_delete()
    store.updated_by = current_user.id
    session.add(store)
    await session.commit()

    return store
