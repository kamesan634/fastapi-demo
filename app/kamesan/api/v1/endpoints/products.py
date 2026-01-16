"""
商品管理 API 端點

提供商品的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Product
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ProductResponse], summary="取得商品列表")
async def get_products(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    supplier_id: Optional[int] = Query(default=None),
):
    """取得商品列表"""
    statement = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.tax_type),
        )
        .where(Product.is_deleted == False)
    )

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Product.code.ilike(search_pattern))
            | (Product.name.ilike(search_pattern))
            | (Product.barcode.ilike(search_pattern))
        )

    if is_active is not None:
        statement = statement.where(Product.is_active == is_active)

    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)

    if supplier_id is not None:
        statement = statement.where(Product.supplier_id == supplier_id)

    count_result = await session.execute(
        select(Product).where(Product.is_deleted == False)
    )
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Product.id.desc())

    result = await session.execute(statement)
    products = result.scalars().all()

    return PaginatedResponse.create(items=products, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="建立商品")
async def create_product(
    product_data: ProductCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品"""
    # 檢查代碼是否已存在
    statement = select(Product).where(Product.code == product_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="商品代碼已存在")

    # 檢查條碼是否已存在
    if product_data.barcode:
        statement = select(Product).where(Product.barcode == product_data.barcode)
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="商品條碼已存在")

    product = Product(**product_data.model_dump(), created_by=current_user.id)
    session.add(product)
    await session.commit()
    await session.refresh(product)

    return product


@router.get("/{product_id}", response_model=ProductResponse, summary="取得單一商品")
async def get_product(product_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一商品"""
    statement = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.tax_type),
        )
        .where(Product.id == product_id, Product.is_deleted == False)
    )
    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    return product


@router.get("/barcode/{barcode}", response_model=ProductResponse, summary="依條碼取得商品")
async def get_product_by_barcode(barcode: str, session: SessionDep, current_user: CurrentUser):
    """依條碼取得商品"""
    statement = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.tax_type),
        )
        .where(Product.barcode == barcode, Product.is_deleted == False)
    )
    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    return product


@router.put("/{product_id}", response_model=ProductResponse, summary="更新商品")
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新商品"""
    statement = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    update_data = product_data.model_dump(exclude_unset=True)

    # 檢查條碼是否重複
    if "barcode" in update_data and update_data["barcode"] != product.barcode:
        statement = select(Product).where(Product.barcode == update_data["barcode"])
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="商品條碼已存在")

    for field, value in update_data.items():
        setattr(product, field, value)

    product.updated_by = current_user.id
    session.add(product)
    await session.commit()
    await session.refresh(product)

    return product


@router.delete("/{product_id}", response_model=ProductResponse, summary="刪除商品")
async def delete_product(product_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除商品"""
    statement = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.soft_delete()
    product.updated_by = current_user.id
    session.add(product)
    await session.commit()

    return product
