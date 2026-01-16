"""
商品類別管理 API 端點

提供商品類別的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Category
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.product import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CategoryResponse], summary="取得類別列表")
async def get_categories(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    parent_id: Optional[int] = Query(default=None),
):
    """取得類別列表"""
    statement = select(Category).where(Category.is_deleted == False)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Category.code.ilike(search_pattern)) | (Category.name.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Category.is_active == is_active)

    if parent_id is not None:
        statement = statement.where(Category.parent_id == parent_id)

    count_result = await session.execute(
        select(Category).where(Category.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Category.sort_order, Category.id)

    result = await session.execute(statement)
    categories = result.scalars().all()

    return PaginatedResponse.create(items=categories, total=total, page=page, page_size=page_size)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="建立類別")
async def create_category(
    category_data: CategoryCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立類別"""
    statement = select(Category).where(Category.code == category_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="類別代碼已存在")

    category = Category(**category_data.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)

    return category


@router.get("/{category_id}", response_model=CategoryResponse, summary="取得單一類別")
async def get_category(category_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一類別"""
    statement = select(Category).where(Category.id == category_id, Category.is_deleted == False)
    result = await session.execute(statement)
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(status_code=404, detail="類別不存在")

    return category


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新類別")
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新類別"""
    statement = select(Category).where(Category.id == category_id, Category.is_deleted == False)
    result = await session.execute(statement)
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(status_code=404, detail="類別不存在")

    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    session.add(category)
    await session.commit()
    await session.refresh(category)

    return category


@router.delete("/{category_id}", response_model=CategoryResponse, summary="刪除類別")
async def delete_category(category_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除類別"""
    statement = select(Category).where(Category.id == category_id, Category.is_deleted == False)
    result = await session.execute(statement)
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(status_code=404, detail="類別不存在")

    category.soft_delete()
    session.add(category)
    await session.commit()

    return category
