"""
銷售退貨管理 API 端點

提供銷售退貨單的 CRUD 操作與退貨處理功能。
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.customer import Customer, PointsLog, PointsLogType
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    SalesReturn,
    SalesReturnItem,
    SalesReturnStatus,
)
from app.kamesan.models.product import Product
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.sales_return import (
    SalesReturnApproveRequest,
    SalesReturnCreate,
    SalesReturnRejectRequest,
    SalesReturnResponse,
    SalesReturnSummary,
    SalesReturnUpdate,
)

router = APIRouter()


def generate_return_number() -> str:
    """產生退貨單號"""
    now = datetime.now(timezone.utc)
    return f"RTN{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@router.get(
    "", response_model=PaginatedResponse[SalesReturnSummary], summary="取得退貨單列表"
)
async def get_sales_returns(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[SalesReturnStatus] = Query(default=None, description="退貨狀態"),
    order_id: Optional[int] = Query(default=None, description="原訂單 ID"),
):
    """取得退貨單列表"""
    statement = select(SalesReturn)

    if status is not None:
        statement = statement.where(SalesReturn.status == status)

    if order_id is not None:
        statement = statement.where(SalesReturn.order_id == order_id)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(SalesReturn.id.desc())

    result = await session.execute(statement)
    returns = result.scalars().all()

    return PaginatedResponse.create(
        items=returns, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=SalesReturnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立退貨單",
)
async def create_sales_return(
    return_data: SalesReturnCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    建立退貨單

    根據原訂單建立退貨申請，記錄退貨商品明細。
    """
    # 查詢原訂單
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == return_data.order_id)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="原訂單不存在")

    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="只有已完成的訂單才能退貨")

    # 建立退貨單主檔
    sales_return = SalesReturn(
        return_number=generate_return_number(),
        order_id=order.id,
        store_id=order.store_id,
        customer_id=order.customer_id,
        status=SalesReturnStatus.PENDING,
        reason=return_data.reason,
        reason_detail=return_data.reason_detail,
        notes=return_data.notes,
        created_by=current_user.id,
    )

    session.add(sales_return)
    await session.flush()

    # 建立退貨明細
    total_amount = Decimal("0.00")

    for item_data in return_data.items:
        # 查詢商品
        statement = select(Product).where(Product.id == item_data.product_id)
        result = await session.execute(statement)
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=400, detail=f"商品 ID {item_data.product_id} 不存在"
            )

        # 若有指定原訂單明細，驗證並取得單價
        unit_price = item_data.unit_price
        if item_data.order_item_id:
            order_item = next(
                (i for i in order.items if i.id == item_data.order_item_id), None
            )
            if order_item is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"原訂單明細 ID {item_data.order_item_id} 不存在",
                )
            if order_item.product_id != item_data.product_id:
                raise HTTPException(
                    status_code=400, detail="訂單明細的商品與指定商品不符"
                )
            if item_data.quantity > order_item.quantity:
                raise HTTPException(
                    status_code=400, detail=f"退貨數量不能超過原購買數量 {order_item.quantity}"
                )
            if unit_price is None:
                unit_price = order_item.unit_price
        else:
            if unit_price is None:
                unit_price = product.selling_price

        # 計算小計
        item_subtotal = unit_price * item_data.quantity

        # 建立明細
        return_item = SalesReturnItem(
            sales_return_id=sales_return.id,
            order_item_id=item_data.order_item_id,
            product_id=product.id,
            product_name=product.name,
            quantity=item_data.quantity,
            unit_price=unit_price,
            subtotal=item_subtotal,
        )
        session.add(return_item)

        total_amount += item_subtotal

    # 更新退款金額
    sales_return.total_amount = total_amount

    await session.commit()

    # 重新查詢完整退貨單
    statement = (
        select(SalesReturn)
        .options(selectinload(SalesReturn.items))
        .where(SalesReturn.id == sales_return.id)
    )
    result = await session.execute(statement)
    sales_return = result.scalar_one()

    return sales_return


@router.get(
    "/{return_id}", response_model=SalesReturnResponse, summary="取得單一退貨單"
)
async def get_sales_return(
    return_id: int, session: SessionDep, current_user: CurrentUser
):
    """取得單一退貨單"""
    statement = (
        select(SalesReturn)
        .options(selectinload(SalesReturn.items))
        .where(SalesReturn.id == return_id)
    )
    result = await session.execute(statement)
    sales_return = result.scalar_one_or_none()

    if sales_return is None:
        raise HTTPException(status_code=404, detail="退貨單不存在")

    return sales_return


@router.put("/{return_id}", response_model=SalesReturnResponse, summary="更新退貨單")
async def update_sales_return(
    return_id: int,
    return_data: SalesReturnUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新退貨單"""
    statement = select(SalesReturn).where(SalesReturn.id == return_id)
    result = await session.execute(statement)
    sales_return = result.scalar_one_or_none()

    if sales_return is None:
        raise HTTPException(status_code=404, detail="退貨單不存在")

    if sales_return.status not in [
        SalesReturnStatus.PENDING,
        SalesReturnStatus.APPROVED,
    ]:
        raise HTTPException(status_code=400, detail="此退貨單狀態無法修改")

    update_data = return_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sales_return, field, value)

    sales_return.updated_by = current_user.id
    session.add(sales_return)
    await session.commit()
    await session.refresh(sales_return)

    return sales_return


@router.post(
    "/{return_id}/approve", response_model=SalesReturnResponse, summary="核准退貨單"
)
async def approve_sales_return(
    return_id: int,
    approve_data: SalesReturnApproveRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """核准退貨單"""
    statement = select(SalesReturn).where(SalesReturn.id == return_id)
    result = await session.execute(statement)
    sales_return = result.scalar_one_or_none()

    if sales_return is None:
        raise HTTPException(status_code=404, detail="退貨單不存在")

    if sales_return.status != SalesReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待處理的退貨單才能核准")

    sales_return.status = SalesReturnStatus.APPROVED
    if approve_data.notes:
        existing_notes = sales_return.notes or ""
        sales_return.notes = (
            f"{existing_notes}\n[核准備註] {approve_data.notes}".strip()
        )
    sales_return.updated_by = current_user.id

    session.add(sales_return)
    await session.commit()
    await session.refresh(sales_return)

    return sales_return


@router.post(
    "/{return_id}/complete", response_model=SalesReturnResponse, summary="完成退貨"
)
async def complete_sales_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    完成退貨處理

    執行以下操作：
    1. 回補庫存
    2. 扣除客戶點數（若有）
    3. 更新訂單狀態
    """
    statement = (
        select(SalesReturn)
        .options(selectinload(SalesReturn.items))
        .where(SalesReturn.id == return_id)
    )
    result = await session.execute(statement)
    sales_return = result.scalar_one_or_none()

    if sales_return is None:
        raise HTTPException(status_code=404, detail="退貨單不存在")

    if sales_return.status != SalesReturnStatus.APPROVED:
        raise HTTPException(status_code=400, detail="只有已核准的退貨單才能完成")

    # 回補庫存
    warehouse_id = 1  # 預設倉庫，實際應從門市取得
    for item in sales_return.items:
        # 查詢庫存
        statement = select(Inventory).where(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == warehouse_id,
        )
        result = await session.execute(statement)
        inventory = result.scalar_one_or_none()

        if inventory is None:
            # 建立新庫存記錄
            inventory = Inventory(
                product_id=item.product_id,
                warehouse_id=warehouse_id,
                quantity=0,
                created_by=current_user.id,
            )
            session.add(inventory)
            await session.flush()

        # 回補庫存
        before_qty = inventory.quantity
        inventory.quantity += item.quantity
        session.add(inventory)

        # 建立庫存異動記錄
        transaction = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=warehouse_id,
            transaction_type=TransactionType.RETURN,
            quantity=item.quantity,
            before_quantity=before_qty,
            after_quantity=inventory.quantity,
            reference_type="SalesReturn",
            reference_id=sales_return.id,
            created_by=current_user.id,
        )
        session.add(transaction)

    # 扣除客戶點數（若原訂單有給點）
    if sales_return.customer_id:
        statement = select(Customer).where(Customer.id == sales_return.customer_id)
        result = await session.execute(statement)
        customer = result.scalar_one_or_none()

        if customer:
            # 查詢原訂單的點數獲得記錄
            statement = select(Order).where(Order.id == sales_return.order_id)
            result = await session.execute(statement)
            order = result.scalar_one_or_none()

            if order and order.points_earned > 0:
                # 計算應扣除的點數（按退款金額比例）
                points_ratio = sales_return.total_amount / order.total_amount
                points_to_deduct = int(order.points_earned * points_ratio)

                if points_to_deduct > 0:
                    # 扣除點數
                    customer.points = max(0, customer.points - points_to_deduct)
                    sales_return.points_deducted = points_to_deduct

                    # 建立點數扣除記錄
                    points_log = PointsLog(
                        customer_id=customer.id,
                        type=PointsLogType.REFUND,
                        points=-points_to_deduct,
                        balance=customer.points,
                        reference_type="SalesReturn",
                        reference_id=sales_return.id,
                        description=f"退貨扣除點數 (退貨單: {sales_return.return_number})",
                        created_by=current_user.id,
                    )
                    session.add(points_log)
                    session.add(customer)

    # 更新退貨單狀態
    sales_return.status = SalesReturnStatus.COMPLETED
    sales_return.updated_by = current_user.id
    session.add(sales_return)

    await session.commit()
    await session.refresh(sales_return)

    return sales_return


@router.post(
    "/{return_id}/reject", response_model=SalesReturnResponse, summary="拒絕退貨單"
)
async def reject_sales_return(
    return_id: int,
    reject_data: SalesReturnRejectRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """拒絕退貨單"""
    statement = select(SalesReturn).where(SalesReturn.id == return_id)
    result = await session.execute(statement)
    sales_return = result.scalar_one_or_none()

    if sales_return is None:
        raise HTTPException(status_code=404, detail="退貨單不存在")

    if sales_return.status != SalesReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待處理的退貨單才能拒絕")

    sales_return.status = SalesReturnStatus.REJECTED
    existing_notes = sales_return.notes or ""
    sales_return.notes = f"{existing_notes}\n[拒絕原因] {reject_data.reason}".strip()
    sales_return.updated_by = current_user.id

    session.add(sales_return)
    await session.commit()
    await session.refresh(sales_return)

    return sales_return
