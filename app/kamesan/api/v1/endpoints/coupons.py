"""
優惠券管理 API 端點

提供優惠券的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.promotion import Coupon
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.promotion import CouponCreate, CouponResponse, CouponUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CouponResponse], summary="取得優惠券列表")
async def get_coupons(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    is_used: Optional[bool] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
):
    """取得優惠券列表"""
    statement = select(Coupon)

    if is_active is not None:
        statement = statement.where(Coupon.is_active == is_active)

    if is_used is not None:
        statement = statement.where(Coupon.is_used == is_used)

    if customer_id is not None:
        statement = statement.where(Coupon.customer_id == customer_id)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Coupon.id.desc())

    result = await session.execute(statement)
    coupons = result.scalars().all()

    return PaginatedResponse.create(items=coupons, total=total, page=page, page_size=page_size)


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED, summary="建立優惠券")
async def create_coupon(
    coupon_data: CouponCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立優惠券"""
    statement = select(Coupon).where(Coupon.code == coupon_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="優惠券代碼已存在")

    coupon = Coupon(**coupon_data.model_dump(), created_by=current_user.id)
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)

    return coupon


@router.get("/{coupon_id}", response_model=CouponResponse, summary="取得單一優惠券")
async def get_coupon(coupon_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一優惠券"""
    statement = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(statement)
    coupon = result.scalar_one_or_none()

    if coupon is None:
        raise HTTPException(status_code=404, detail="優惠券不存在")

    return coupon


@router.get("/code/{code}", response_model=CouponResponse, summary="依代碼取得優惠券")
async def get_coupon_by_code(code: str, session: SessionDep, current_user: CurrentUser):
    """依代碼取得優惠券"""
    statement = select(Coupon).where(Coupon.code == code)
    result = await session.execute(statement)
    coupon = result.scalar_one_or_none()

    if coupon is None:
        raise HTTPException(status_code=404, detail="優惠券不存在")

    return coupon


@router.put("/{coupon_id}", response_model=CouponResponse, summary="更新優惠券")
async def update_coupon(
    coupon_id: int,
    coupon_data: CouponUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新優惠券"""
    statement = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(statement)
    coupon = result.scalar_one_or_none()

    if coupon is None:
        raise HTTPException(status_code=404, detail="優惠券不存在")

    if coupon.is_used:
        raise HTTPException(status_code=400, detail="已使用的優惠券無法修改")

    update_data = coupon_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    coupon.updated_by = current_user.id
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)

    return coupon


@router.delete("/{coupon_id}", response_model=CouponResponse, summary="刪除優惠券")
async def delete_coupon(coupon_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除優惠券"""
    statement = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(statement)
    coupon = result.scalar_one_or_none()

    if coupon is None:
        raise HTTPException(status_code=404, detail="優惠券不存在")

    if coupon.is_used:
        raise HTTPException(status_code=400, detail="已使用的優惠券無法刪除")

    await session.delete(coupon)
    await session.commit()

    return coupon
