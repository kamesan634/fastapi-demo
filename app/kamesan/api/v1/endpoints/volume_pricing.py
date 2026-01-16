"""
量販價管理 API 端點

提供量販價的 CRUD 操作與價格計算功能。
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.pricing import ProductPromoPrice, VolumePricing
from app.kamesan.models.product import Product
from app.kamesan.models.customer import CustomerLevel
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.pricing import (
    CalculatePriceRequest,
    CalculatePriceResponse,
    ProductVolumePricingResponse,
    PromoPriceCreate,
    PromoPriceResponse,
    PromoPriceUpdate,
    VolumePricingCreate,
    VolumePricingResponse,
    VolumePricingTier,
    VolumePricingUpdate,
)

router = APIRouter()


# ==========================================
# 量販價 API
# ==========================================
@router.get(
    "/products/{product_id}/volume-pricing",
    response_model=ProductVolumePricingResponse,
    summary="取得商品量販價",
)
async def get_volume_pricing(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得指定商品的量販價設定"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 取得量販價列表
    stmt = (
        select(VolumePricing)
        .where(
            VolumePricing.product_id == product_id,
            VolumePricing.is_deleted == False,
            VolumePricing.is_active == True,
        )
        .order_by(VolumePricing.min_quantity)
    )
    result = await session.execute(stmt)
    pricings = result.scalars().all()

    # 組裝回應
    tiers = []
    for idx, pricing in enumerate(pricings):
        max_str = str(pricing.max_quantity) if pricing.max_quantity else "+"
        quantity_range = (
            f"{pricing.min_quantity}-{pricing.max_quantity}"
            if pricing.max_quantity
            else f"{pricing.min_quantity}+"
        )

        # 計算折扣百分比
        discount_pct = None
        if product.selling_price > 0:
            discount_pct = round(
                (1 - pricing.unit_price / product.selling_price) * 100, 2
            )

        tiers.append(
            VolumePricingTier(
                tier=idx + 1,
                quantity_range=quantity_range,
                min_quantity=pricing.min_quantity,
                max_quantity=pricing.max_quantity,
                unit_price=pricing.unit_price,
                discount_percentage=Decimal(str(discount_pct)) if discount_pct else None,
            )
        )

    return ProductVolumePricingResponse(
        product_id=product.id,
        product_name=product.name,
        standard_price=product.selling_price,
        tiers=tiers,
    )


@router.post(
    "/products/{product_id}/volume-pricing",
    response_model=VolumePricingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立量販價",
)
async def create_volume_pricing(
    product_id: int,
    pricing_data: VolumePricingCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品量販價"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 檢查數量區間是否重疊
    stmt = select(VolumePricing).where(
        VolumePricing.product_id == product_id,
        VolumePricing.is_deleted == False,
        VolumePricing.is_active == True,
    )
    result = await session.execute(stmt)
    existing_pricings = result.scalars().all()

    for existing in existing_pricings:
        # 檢查是否重疊
        new_min = pricing_data.min_quantity
        new_max = pricing_data.max_quantity
        exist_min = existing.min_quantity
        exist_max = existing.max_quantity

        # 如果區間重疊則報錯
        if new_max is None:
            new_max = float("inf")
        if exist_max is None:
            exist_max = float("inf")

        if not (new_max < exist_min or new_min > exist_max):
            raise HTTPException(
                status_code=400,
                detail=f"數量區間與現有設定重疊（{existing.min_quantity}-{existing.max_quantity or '無限'}）",
            )

    pricing = VolumePricing(
        product_id=product_id,
        **pricing_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(pricing)
    await session.commit()
    await session.refresh(pricing)

    return pricing


@router.put(
    "/volume-pricing/{pricing_id}",
    response_model=VolumePricingResponse,
    summary="更新量販價",
)
async def update_volume_pricing(
    pricing_id: int,
    pricing_data: VolumePricingUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新量販價"""
    stmt = select(VolumePricing).where(
        VolumePricing.id == pricing_id,
        VolumePricing.is_deleted == False,
    )
    result = await session.execute(stmt)
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="量販價設定不存在")

    update_data = pricing_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pricing, field, value)

    pricing.updated_by = current_user.id
    session.add(pricing)
    await session.commit()
    await session.refresh(pricing)

    return pricing


@router.delete(
    "/volume-pricing/{pricing_id}",
    response_model=MessageResponse,
    summary="刪除量販價",
)
async def delete_volume_pricing(
    pricing_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除量販價（軟刪除）"""
    stmt = select(VolumePricing).where(
        VolumePricing.id == pricing_id,
        VolumePricing.is_deleted == False,
    )
    result = await session.execute(stmt)
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(status_code=404, detail="量販價設定不存在")

    pricing.is_deleted = True
    pricing.updated_by = current_user.id
    session.add(pricing)
    await session.commit()

    return MessageResponse(message="量販價設定已刪除")


# ==========================================
# 促銷價 API
# ==========================================
@router.get(
    "/products/{product_id}/promo-prices",
    response_model=List[PromoPriceResponse],
    summary="取得商品促銷價列表",
)
async def get_promo_prices(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    active_only: bool = Query(default=False, description="僅顯示有效促銷"),
):
    """取得指定商品的促銷價列表"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    stmt = select(ProductPromoPrice).where(
        ProductPromoPrice.product_id == product_id,
        ProductPromoPrice.is_deleted == False,
    )

    if active_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(
            ProductPromoPrice.is_active == True,
            ProductPromoPrice.start_date <= now,
            ProductPromoPrice.end_date >= now,
        )

    stmt = stmt.order_by(ProductPromoPrice.start_date.desc())
    result = await session.execute(stmt)
    promo_prices = result.scalars().all()

    # 添加 is_valid 欄位
    response = []
    now = datetime.now(timezone.utc)
    for promo in promo_prices:
        promo_dict = PromoPriceResponse.model_validate(promo)
        promo_dict.is_valid = (
            promo.is_active and promo.start_date <= now <= promo.end_date
        )
        response.append(promo_dict)

    return response


@router.post(
    "/products/{product_id}/promo-prices",
    response_model=PromoPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立促銷價",
)
async def create_promo_price(
    product_id: int,
    promo_data: PromoPriceCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立商品促銷價"""
    # 驗證商品存在
    stmt = select(Product).where(Product.id == product_id, Product.is_deleted == False)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    promo = ProductPromoPrice(
        product_id=product_id,
        **promo_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)

    return promo


@router.put(
    "/promo-prices/{promo_id}",
    response_model=PromoPriceResponse,
    summary="更新促銷價",
)
async def update_promo_price(
    promo_id: int,
    promo_data: PromoPriceUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新促銷價"""
    stmt = select(ProductPromoPrice).where(
        ProductPromoPrice.id == promo_id,
        ProductPromoPrice.is_deleted == False,
    )
    result = await session.execute(stmt)
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="促銷價設定不存在")

    update_data = promo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promo, field, value)

    promo.updated_by = current_user.id
    session.add(promo)
    await session.commit()
    await session.refresh(promo)

    return promo


@router.delete(
    "/promo-prices/{promo_id}",
    response_model=MessageResponse,
    summary="刪除促銷價",
)
async def delete_promo_price(
    promo_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除促銷價（軟刪除）"""
    stmt = select(ProductPromoPrice).where(
        ProductPromoPrice.id == promo_id,
        ProductPromoPrice.is_deleted == False,
    )
    result = await session.execute(stmt)
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="促銷價設定不存在")

    promo.is_deleted = True
    promo.updated_by = current_user.id
    session.add(promo)
    await session.commit()

    return MessageResponse(message="促銷價設定已刪除")


# ==========================================
# 價格計算 API
# ==========================================
@router.post(
    "/calculate-price",
    response_model=CalculatePriceResponse,
    summary="計算商品價格",
)
async def calculate_price(
    request: CalculatePriceRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    計算商品的最終價格

    價格優先順序:
    1. 促銷價（限時特價）
    2. 會員價（會員專屬）
    3. 量販價（購買數量達標）
    4. 標準售價（一般定價）
    """
    # 取得商品
    stmt = select(Product).where(
        Product.id == request.product_id, Product.is_deleted == False
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    standard_price = product.selling_price
    applied_price = standard_price
    price_type = "標準"

    # 1. 檢查促銷價
    now = datetime.now(timezone.utc)
    stmt = select(ProductPromoPrice).where(
        ProductPromoPrice.product_id == request.product_id,
        ProductPromoPrice.is_deleted == False,
        ProductPromoPrice.is_active == True,
        ProductPromoPrice.start_date <= now,
        ProductPromoPrice.end_date >= now,
    )
    result = await session.execute(stmt)
    promo = result.scalars().first()

    if promo:
        applied_price = promo.promo_price
        price_type = "促銷"
    else:
        # 2. 檢查會員價
        if request.customer_level_id:
            stmt = select(CustomerLevel).where(
                CustomerLevel.id == request.customer_level_id
            )
            result = await session.execute(stmt)
            level = result.scalar_one_or_none()

            if level and level.discount_rate and level.discount_rate > 0:
                member_price = standard_price * (1 - level.discount_rate / 100)
                if member_price < applied_price:
                    applied_price = member_price
                    price_type = "會員"

        # 3. 檢查量販價
        stmt = (
            select(VolumePricing)
            .where(
                VolumePricing.product_id == request.product_id,
                VolumePricing.is_deleted == False,
                VolumePricing.is_active == True,
                VolumePricing.min_quantity <= request.quantity,
            )
            .order_by(VolumePricing.min_quantity.desc())
        )
        result = await session.execute(stmt)
        volume_pricing = result.scalars().first()

        if volume_pricing:
            # 檢查最高數量限制
            if (
                volume_pricing.max_quantity is None
                or request.quantity <= volume_pricing.max_quantity
            ):
                if volume_pricing.unit_price < applied_price:
                    applied_price = volume_pricing.unit_price
                    price_type = "量販"

    # 計算結果
    total_amount = applied_price * request.quantity
    discount_amount = (standard_price - applied_price) * request.quantity
    discount_percentage = (
        round((1 - applied_price / standard_price) * 100, 2)
        if standard_price > 0
        else Decimal("0")
    )

    return CalculatePriceResponse(
        product_id=request.product_id,
        quantity=request.quantity,
        standard_unit_price=standard_price,
        applied_unit_price=applied_price,
        price_type=price_type,
        total_amount=total_amount,
        discount_amount=discount_amount,
        discount_percentage=Decimal(str(discount_percentage)),
    )
