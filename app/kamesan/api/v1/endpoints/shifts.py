"""
班次管理 API 端點

提供班次的開班、關班和查詢功能。
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import func, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.shift import CashierShift, ShiftStatus
from app.kamesan.models.store import Store
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.shift import (
    ShiftCloseRequest,
    ShiftOpenRequest,
    ShiftReportResponse,
    ShiftResponse,
    ShiftSummary,
)

router = APIRouter()


@router.post(
    "/open",
    response_model=ShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="開班",
)
async def open_shift(
    shift_data: ShiftOpenRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    開班

    收銀員開始營業，記錄開班現金。
    """
    # 檢查門市是否存在
    store = await session.get(Store, shift_data.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="門市不存在")

    # 檢查是否有未關班的班次
    statement = select(CashierShift).where(
        CashierShift.cashier_id == current_user.id,
        CashierShift.status == ShiftStatus.OPEN,
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您有未關班的班次，請先關班")

    # 建立新班次
    shift = CashierShift(
        store_id=shift_data.store_id,
        pos_id=shift_data.pos_id,
        cashier_id=current_user.id,
        shift_date=date.today(),
        start_time=datetime.now(timezone.utc),
        opening_cash=shift_data.opening_cash,
        expected_cash=shift_data.opening_cash,  # 開班時預期現金 = 開班現金
        status=ShiftStatus.OPEN,
        notes=shift_data.notes,
        created_by=current_user.id,
    )

    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    return shift


@router.post(
    "/{shift_id}/close",
    response_model=ShiftResponse,
    summary="關班",
)
async def close_shift(
    shift_id: int,
    close_data: ShiftCloseRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    關班

    收銀員結束營業，清點現金並計算差異。
    """
    # 取得班次
    shift = await session.get(CashierShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")

    # 檢查權限（只有班次所屬收銀員或主管可以關班）
    if shift.cashier_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限關閉此班次")

    # 檢查狀態
    if shift.status != ShiftStatus.OPEN:
        raise HTTPException(status_code=400, detail="此班次已關班")

    # 計算預期現金（這裡簡化處理，實際應從訂單計算）
    # expected_cash = opening_cash + cash_sales - cash_refunds
    expected_cash = shift.opening_cash + shift.total_cash_sales - shift.total_refunds

    # 計算差異
    cash_difference = close_data.actual_cash - expected_cash

    # 更新班次
    shift.end_time = datetime.now(timezone.utc)
    shift.expected_cash = expected_cash
    shift.actual_cash = close_data.actual_cash
    shift.cash_difference = cash_difference
    shift.difference_note = close_data.difference_note
    shift.status = ShiftStatus.CLOSED
    shift.updated_by = current_user.id

    if close_data.notes:
        shift.notes = (shift.notes or "") + "\n" + close_data.notes

    # 如果差異過大（例如超過 50），需要主管核准
    # 這裡只是標記，實際核准流程可以再擴展
    if abs(cash_difference) > Decimal("50.00"):
        shift.approved_by = None  # 待核准

    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    return shift


@router.get(
    "",
    response_model=PaginatedResponse[ShiftSummary],
    summary="取得班次列表",
)
async def get_shifts(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    store_id: Optional[int] = Query(default=None, description="門市 ID"),
    cashier_id: Optional[int] = Query(default=None, description="收銀員 ID"),
    status: Optional[ShiftStatus] = Query(default=None, description="班次狀態"),
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
):
    """
    取得班次列表

    支援依門市、收銀員、狀態、日期範圍篩選。
    """
    statement = select(CashierShift)

    # 篩選條件
    if store_id:
        statement = statement.where(CashierShift.store_id == store_id)
    if cashier_id:
        statement = statement.where(CashierShift.cashier_id == cashier_id)
    if status:
        statement = statement.where(CashierShift.status == status)
    if start_date:
        statement = statement.where(CashierShift.shift_date >= start_date)
    if end_date:
        statement = statement.where(CashierShift.shift_date <= end_date)

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(
        CashierShift.id.desc()
    )

    result = await session.execute(statement)
    shifts = result.scalars().all()

    return PaginatedResponse.create(
        items=shifts, total=total, page=page, page_size=page_size
    )


@router.get(
    "/current",
    response_model=Optional[ShiftResponse],
    summary="取得目前開班中的班次",
)
async def get_current_shift(
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得目前登入使用者開班中的班次

    如果沒有開班中的班次則回傳 null。
    """
    statement = select(CashierShift).where(
        CashierShift.cashier_id == current_user.id,
        CashierShift.status == ShiftStatus.OPEN,
    )
    result = await session.execute(statement)
    shift = result.scalar_one_or_none()

    return shift


@router.get(
    "/{shift_id}",
    response_model=ShiftResponse,
    summary="取得單一班次",
)
async def get_shift(
    shift_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依 ID 取得單一班次詳情
    """
    shift = await session.get(CashierShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")

    return shift


@router.get(
    "/{shift_id}/report",
    response_model=ShiftReportResponse,
    summary="取得班次報表",
)
async def get_shift_report(
    shift_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得班次報表

    包含銷售明細、付款方式統計等。
    """
    shift = await session.get(CashierShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")

    # 這裡可以擴展查詢訂單明細
    # 目前先回傳基本資訊
    sales_by_payment_method = {
        "cash": float(shift.total_cash_sales),
        "card": float(shift.total_card_sales),
        "other": float(shift.total_other_sales),
    }

    return ShiftReportResponse(
        shift=ShiftResponse.model_validate(shift),
        sales_by_payment_method=sales_by_payment_method,
        sales_by_category={},  # 可擴展
        cash_count_detail=None,  # 可擴展
    )


@router.put(
    "/{shift_id}/approve",
    response_model=ShiftResponse,
    summary="核准班次差異",
)
async def approve_shift(
    shift_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    主管核准班次現金差異

    當現金差異超過設定值時需要主管核准。
    """
    # 檢查權限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要主管權限")

    shift = await session.get(CashierShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")

    if shift.status != ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="班次尚未關班")

    shift.approved_by = current_user.id
    shift.updated_by = current_user.id

    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    return shift
