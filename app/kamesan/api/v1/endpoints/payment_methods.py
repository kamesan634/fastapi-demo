"""
付款方式管理 API 端點

提供付款方式的 CRUD 操作。

端點：
- GET /payment-methods: 取得付款方式列表
- POST /payment-methods: 建立付款方式
- GET /payment-methods/{id}: 取得單一付款方式
- PUT /payment-methods/{id}: 更新付款方式
- DELETE /payment-methods/{id}: 刪除付款方式
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.order import PaymentMethodSetting
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.payment_method import (
    PaymentMethodSettingCreate,
    PaymentMethodSettingResponse,
    PaymentMethodSettingUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[PaymentMethodSettingResponse],
    summary="取得付款方式列表",
)
async def get_payment_methods(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None, description="篩選啟用狀態"),
):
    """
    取得付款方式列表

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        page: 頁碼
        page_size: 每頁筆數
        is_active: 篩選啟用狀態

    回傳值：
        PaginatedResponse: 分頁付款方式列表
    """
    statement = select(PaymentMethodSetting)

    if is_active is not None:
        statement = statement.where(PaymentMethodSetting.is_active == is_active)

    # 計算總數
    count_result = await session.execute(statement)
    total = len(count_result.all())

    # 分頁查詢
    offset = (page - 1) * page_size
    statement = (
        statement.offset(offset)
        .limit(page_size)
        .order_by(PaymentMethodSetting.sort_order, PaymentMethodSetting.id)
    )

    result = await session.execute(statement)
    payment_methods = result.scalars().all()

    return PaginatedResponse.create(
        items=payment_methods, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=PaymentMethodSettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立付款方式",
)
async def create_payment_method(
    payment_method_data: PaymentMethodSettingCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立付款方式

    參數：
        payment_method_data: 付款方式資料
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        PaymentMethodSettingResponse: 建立的付款方式

    例外：
        400: 付款方式代碼已存在
    """
    # 檢查代碼是否已存在
    statement = select(PaymentMethodSetting).where(
        PaymentMethodSetting.code == payment_method_data.code
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="付款方式代碼已存在")

    # 建立付款方式
    payment_method = PaymentMethodSetting(
        **payment_method_data.model_dump(),
        created_by=current_user.id,
    )
    session.add(payment_method)
    await session.commit()
    await session.refresh(payment_method)

    return payment_method


@router.get(
    "/{payment_method_id}",
    response_model=PaymentMethodSettingResponse,
    summary="取得單一付款方式",
)
async def get_payment_method(
    payment_method_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得單一付款方式

    參數：
        payment_method_id: 付款方式 ID
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        PaymentMethodSettingResponse: 付款方式資料

    例外：
        404: 付款方式不存在
    """
    statement = select(PaymentMethodSetting).where(
        PaymentMethodSetting.id == payment_method_id
    )
    result = await session.execute(statement)
    payment_method = result.scalar_one_or_none()

    if payment_method is None:
        raise HTTPException(status_code=404, detail="付款方式不存在")

    return payment_method


@router.put(
    "/{payment_method_id}",
    response_model=PaymentMethodSettingResponse,
    summary="更新付款方式",
)
async def update_payment_method(
    payment_method_id: int,
    payment_method_data: PaymentMethodSettingUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    更新付款方式

    參數：
        payment_method_id: 付款方式 ID
        payment_method_data: 更新資料
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        PaymentMethodSettingResponse: 更新後的付款方式

    例外：
        404: 付款方式不存在
    """
    statement = select(PaymentMethodSetting).where(
        PaymentMethodSetting.id == payment_method_id
    )
    result = await session.execute(statement)
    payment_method = result.scalar_one_or_none()

    if payment_method is None:
        raise HTTPException(status_code=404, detail="付款方式不存在")

    # 更新欄位
    update_data = payment_method_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment_method, field, value)

    payment_method.updated_by = current_user.id
    session.add(payment_method)
    await session.commit()
    await session.refresh(payment_method)

    return payment_method


@router.delete(
    "/{payment_method_id}",
    response_model=PaymentMethodSettingResponse,
    summary="刪除付款方式",
)
async def delete_payment_method(
    payment_method_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    刪除付款方式（停用）

    參數：
        payment_method_id: 付款方式 ID
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        PaymentMethodSettingResponse: 停用的付款方式

    例外：
        404: 付款方式不存在
    """
    statement = select(PaymentMethodSetting).where(
        PaymentMethodSetting.id == payment_method_id
    )
    result = await session.execute(statement)
    payment_method = result.scalar_one_or_none()

    if payment_method is None:
        raise HTTPException(status_code=404, detail="付款方式不存在")

    # 停用而非刪除
    payment_method.is_active = False
    payment_method.updated_by = current_user.id
    session.add(payment_method)
    await session.commit()
    await session.refresh(payment_method)

    return payment_method
