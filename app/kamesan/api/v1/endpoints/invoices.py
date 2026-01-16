"""
發票管理 API 端點

提供發票的開立、查詢、列印、作廢功能。
"""

import random
import string
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import func, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.invoice import CarrierType, Invoice, InvoiceType
from app.kamesan.models.order import Order
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceSummary,
    InvoiceVoidRequest,
)

router = APIRouter()


def generate_invoice_number() -> str:
    """
    產生發票號碼

    格式：字軌 (2 碼大寫字母) + 流水號 (8 碼數字)
    實際應用中應從資料庫取得目前字軌和序號
    """
    # 簡化版本，實際應從系統參數或專用表格取得
    track = "".join(random.choices(string.ascii_uppercase, k=2))
    number = "".join(random.choices(string.digits, k=8))
    return f"{track}{number}"


def generate_random_number() -> str:
    """產生 4 碼隨機碼"""
    return "".join(random.choices(string.digits, k=4))


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="開立發票",
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    開立發票

    根據訂單資訊開立電子發票。
    """
    # 檢查訂單是否存在
    order = await session.get(Order, invoice_data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")

    # 檢查訂單是否已開立發票
    statement = select(Invoice).where(
        Invoice.order_id == invoice_data.order_id,
        Invoice.void_flag == False,
    )
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此訂單已開立發票")

    # B2B 發票驗證
    if invoice_data.invoice_type == InvoiceType.B2B:
        if not invoice_data.buyer_tax_id:
            raise HTTPException(status_code=400, detail="營業人發票需填寫統一編號")
        if not invoice_data.buyer_name:
            raise HTTPException(status_code=400, detail="營業人發票需填寫買方名稱")

    # 載具發票驗證
    if invoice_data.invoice_type == InvoiceType.B2C_CARRIER:
        if not invoice_data.carrier_type or not invoice_data.carrier_no:
            raise HTTPException(status_code=400, detail="載具發票需填寫載具資訊")

    # 捐贈發票驗證
    if invoice_data.invoice_type == InvoiceType.B2C_DONATE:
        if not invoice_data.donate_code:
            raise HTTPException(status_code=400, detail="捐贈發票需填寫愛心碼")

    # 計算金額（從訂單取得）
    total_amount = order.total_amount
    # 假設稅率 5%
    tax_rate = Decimal("0.05")
    sales_amount = total_amount / (1 + tax_rate)
    tax_amount = total_amount - sales_amount

    # 建立發票
    invoice = Invoice(
        invoice_no=generate_invoice_number(),
        order_id=invoice_data.order_id,
        invoice_date=datetime.now(timezone.utc),
        invoice_type=invoice_data.invoice_type,
        buyer_tax_id=invoice_data.buyer_tax_id,
        buyer_name=invoice_data.buyer_name,
        carrier_type=invoice_data.carrier_type,
        carrier_no=invoice_data.carrier_no,
        donate_code=invoice_data.donate_code,
        sales_amount=sales_amount.quantize(Decimal("0.01")),
        tax_amount=tax_amount.quantize(Decimal("0.01")),
        total_amount=total_amount,
        print_flag=invoice_data.print_flag,
        random_number=generate_random_number(),
        created_by=current_user.id,
    )

    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    return invoice


@router.get(
    "",
    response_model=PaginatedResponse[InvoiceSummary],
    summary="取得發票列表",
)
async def get_invoices(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    invoice_type: Optional[InvoiceType] = Query(default=None, description="發票類型"),
    void_flag: Optional[bool] = Query(default=None, description="是否作廢"),
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
    search: Optional[str] = Query(default=None, description="搜尋（發票號碼、買方名稱）"),
):
    """
    取得發票列表

    支援依類型、作廢狀態、日期範圍篩選。
    """
    statement = select(Invoice)

    # 篩選條件
    if invoice_type:
        statement = statement.where(Invoice.invoice_type == invoice_type)
    if void_flag is not None:
        statement = statement.where(Invoice.void_flag == void_flag)
    if start_date:
        start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        statement = statement.where(Invoice.invoice_date >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        statement = statement.where(Invoice.invoice_date <= end_datetime)
    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (Invoice.invoice_no.ilike(search_pattern))
            | (Invoice.buyer_name.ilike(search_pattern))
        )

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Invoice.id.desc())

    result = await session.execute(statement)
    invoices = result.scalars().all()

    return PaginatedResponse.create(
        items=invoices, total=total, page=page, page_size=page_size
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="取得單一發票",
)
async def get_invoice(
    invoice_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依 ID 取得單一發票詳情
    """
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    return invoice


@router.get(
    "/by-order/{order_id}",
    response_model=Optional[InvoiceResponse],
    summary="依訂單取得發票",
)
async def get_invoice_by_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依訂單 ID 取得發票

    回傳該訂單最新的有效發票（非作廢）
    """
    statement = select(Invoice).where(
        Invoice.order_id == order_id,
        Invoice.void_flag == False,
    ).order_by(Invoice.id.desc())

    result = await session.execute(statement)
    invoice = result.scalar_one_or_none()

    return invoice


@router.post(
    "/{invoice_id}/print",
    response_model=InvoiceResponse,
    summary="列印發票",
)
async def print_invoice(
    invoice_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    標記發票為已列印

    實際列印功能需整合印表機服務。
    """
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    if invoice.void_flag:
        raise HTTPException(status_code=400, detail="作廢發票不可列印")

    # 載具發票不需列印
    if invoice.invoice_type == InvoiceType.B2C_CARRIER:
        raise HTTPException(status_code=400, detail="載具發票無需列印")

    # 捐贈發票不需列印
    if invoice.invoice_type == InvoiceType.B2C_DONATE:
        raise HTTPException(status_code=400, detail="捐贈發票無需列印")

    invoice.print_flag = True
    invoice.updated_by = current_user.id

    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    return invoice


@router.post(
    "/{invoice_id}/void",
    response_model=InvoiceResponse,
    summary="作廢發票",
)
async def void_invoice(
    invoice_id: int,
    void_data: InvoiceVoidRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    作廢發票

    當月發票可作廢，跨月須使用折讓。
    """
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    if invoice.void_flag:
        raise HTTPException(status_code=400, detail="發票已作廢")

    # 檢查是否跨月（簡化檢查）
    now = datetime.now(timezone.utc)
    if invoice.invoice_date.month != now.month or invoice.invoice_date.year != now.year:
        raise HTTPException(
            status_code=400,
            detail="跨月發票不可作廢，請使用折讓功能",
        )

    invoice.void_flag = True
    invoice.void_date = now
    invoice.void_reason = void_data.reason
    invoice.updated_by = current_user.id

    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    return invoice
