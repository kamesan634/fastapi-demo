"""
促銷管理 API 端點

提供促銷活動的 CRUD 操作。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.promotion import Promotion
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.promotion import PromotionCreate, PromotionResponse, PromotionUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PromotionResponse], summary="取得促銷列表")
async def get_promotions(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
):
    """取得促銷列表"""
    statement = select(Promotion)

    if is_active is not None:
        statement = statement.where(Promotion.is_active == is_active)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Promotion.id.desc())

    result = await session.execute(statement)
    promotions = result.scalars().all()

    return PaginatedResponse.create(items=promotions, total=total, page=page, page_size=page_size)


@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED, summary="建立促銷")
async def create_promotion(
    promotion_data: PromotionCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立促銷活動"""
    statement = select(Promotion).where(Promotion.code == promotion_data.code)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="促銷代碼已存在")

    promotion = Promotion(**promotion_data.model_dump(), created_by=current_user.id)
    session.add(promotion)
    await session.commit()
    await session.refresh(promotion)

    return promotion


@router.get("/{promotion_id}", response_model=PromotionResponse, summary="取得單一促銷")
async def get_promotion(promotion_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一促銷活動"""
    statement = select(Promotion).where(Promotion.id == promotion_id)
    result = await session.execute(statement)
    promotion = result.scalar_one_or_none()

    if promotion is None:
        raise HTTPException(status_code=404, detail="促銷活動不存在")

    return promotion


@router.put("/{promotion_id}", response_model=PromotionResponse, summary="更新促銷")
async def update_promotion(
    promotion_id: int,
    promotion_data: PromotionUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新促銷活動"""
    statement = select(Promotion).where(Promotion.id == promotion_id)
    result = await session.execute(statement)
    promotion = result.scalar_one_or_none()

    if promotion is None:
        raise HTTPException(status_code=404, detail="促銷活動不存在")

    update_data = promotion_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promotion, field, value)

    promotion.updated_by = current_user.id
    session.add(promotion)
    await session.commit()
    await session.refresh(promotion)

    return promotion


@router.delete("/{promotion_id}", response_model=PromotionResponse, summary="刪除促銷")
async def delete_promotion(promotion_id: int, session: SessionDep, current_user: CurrentUser):
    """刪除促銷活動"""
    statement = select(Promotion).where(Promotion.id == promotion_id)
    result = await session.execute(statement)
    promotion = result.scalar_one_or_none()

    if promotion is None:
        raise HTTPException(status_code=404, detail="促銷活動不存在")

    await session.delete(promotion)
    await session.commit()

    return promotion
