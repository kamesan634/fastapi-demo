"""
訂單管理 API 端點

提供訂單的 CRUD 操作與付款功能。
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.customer import Customer
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.order import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.kamesan.models.product import Product
from app.kamesan.models.store import Store
from app.kamesan.schemas.common import MessageResponse, PaginatedResponse
from app.kamesan.schemas.order import OrderCreate, OrderResponse, OrderSummary, OrderUpdate, PaymentCreate, PaymentResponse

router = APIRouter()


def generate_order_number() -> str:
    """產生訂單編號"""
    now = datetime.now(timezone.utc)
    return f"ORD{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@router.get("", response_model=PaginatedResponse[OrderSummary], summary="取得訂單列表")
async def get_orders(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[OrderStatus] = Query(default=None),
    store_id: Optional[int] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
):
    """取得訂單列表"""
    statement = select(Order)

    if status is not None:
        statement = statement.where(Order.status == status)

    if store_id is not None:
        statement = statement.where(Order.store_id == store_id)

    if customer_id is not None:
        statement = statement.where(Order.customer_id == customer_id)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Order.id.desc())

    result = await session.execute(statement)
    orders = result.scalars().all()

    # 建立 OrderSummary 物件，需要額外查詢 customer 和 store 名稱
    summaries = []
    for order in orders:
        customer_name = None
        store_name = None

        if order.customer_id:
            customer_result = await session.execute(
                select(Customer).where(Customer.id == order.customer_id)
            )
            customer = customer_result.scalar_one_or_none()
            customer_name = customer.name if customer else None

        if order.store_id:
            store_result = await session.execute(
                select(Store).where(Store.id == order.store_id)
            )
            store = store_result.scalar_one_or_none()
            store_name = store.name if store else None

        summaries.append(
            OrderSummary(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                total_amount=order.total_amount,
                order_date=order.order_date,
                customer_name=customer_name,
                store_name=store_name,
            )
        )

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="建立訂單")
async def create_order(
    order_data: OrderCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立訂單"""
    # 建立訂單主檔
    order = Order(
        order_number=generate_order_number(),
        store_id=order_data.store_id,
        customer_id=order_data.customer_id,
        status=OrderStatus.PENDING,
        discount_amount=order_data.discount_amount,
        notes=order_data.notes,
        created_by=current_user.id,
    )

    session.add(order)
    await session.flush()  # 取得 order.id

    # 建立訂單明細
    subtotal = Decimal("0.00")
    tax_amount = Decimal("0.00")

    for item_data in order_data.items:
        # 查詢商品
        statement = select(Product).where(Product.id == item_data.product_id)
        result = await session.execute(statement)
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(status_code=400, detail=f"商品 ID {item_data.product_id} 不存在")

        # 計算價格
        unit_price = item_data.unit_price or product.selling_price
        item_subtotal = unit_price * item_data.quantity - item_data.discount_amount
        tax_rate = product.tax_type.rate if product.tax_type else Decimal("0.05")
        item_tax = item_subtotal * tax_rate

        # 建立明細
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=item_data.quantity,
            unit_price=unit_price,
            discount_amount=item_data.discount_amount,
            subtotal=item_subtotal,
            tax_rate=tax_rate,
            tax_amount=item_tax,
        )
        session.add(order_item)

        subtotal += item_subtotal
        tax_amount += item_tax

    # 更新訂單金額
    order.subtotal = subtotal
    order.tax_amount = tax_amount
    order.total_amount = subtotal + tax_amount - order.discount_amount

    # 建立付款記錄
    if order_data.payments:
        for payment_data in order_data.payments:
            payment = Payment(
                order_id=order.id,
                payment_method=payment_data.payment_method,
                amount=payment_data.amount,
                status=PaymentStatus.PENDING,
            )
            session.add(payment)

    await session.commit()

    # 重新查詢完整訂單
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.id == order.id)
    )
    result = await session.execute(statement)
    order = result.scalar_one()

    return order


@router.get("/number/{order_number}", response_model=OrderResponse, summary="用訂單編號取得訂單")
async def get_order_by_number(order_number: str, session: SessionDep, current_user: CurrentUser):
    """用訂單編號取得訂單"""
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.order_number == order_number)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    return order


@router.get("/{order_id}", response_model=OrderResponse, summary="取得單一訂單")
async def get_order(order_id: int, session: SessionDep, current_user: CurrentUser):
    """取得單一訂單"""
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.id == order_id)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    return order


@router.put("/{order_id}", response_model=OrderResponse, summary="更新訂單")
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新訂單"""
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.id == order_id)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
        raise HTTPException(status_code=400, detail="此訂單狀態無法修改")

    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    order.updated_by = current_user.id
    session.add(order)
    await session.commit()

    # 重新查詢以取得包含 items 和 payments 的完整資料
    result = await session.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    order = result.scalar_one()

    return order


@router.post("/{order_id}/complete", response_model=OrderResponse, summary="完成訂單")
async def complete_order(order_id: int, session: SessionDep, current_user: CurrentUser):
    """完成訂單並扣減庫存"""
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.id == order_id)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待處理訂單可以完成")

    # 扣減庫存
    for item in order.items:
        # 查詢庫存（使用門市關聯的倉庫）
        warehouse_id = 1  # 預設倉庫，實際應從門市取得
        statement = select(Inventory).where(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == warehouse_id,
        )
        result = await session.execute(statement)
        inventory = result.scalar_one_or_none()

        if inventory is None or inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"商品 {item.product_name} 庫存不足",
            )

        # 扣減庫存
        before_qty = inventory.quantity
        inventory.quantity -= item.quantity
        session.add(inventory)

        # 建立庫存異動記錄
        transaction = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=warehouse_id,
            transaction_type=TransactionType.SALE,
            quantity=-item.quantity,
            before_quantity=before_qty,
            after_quantity=inventory.quantity,
            reference_type="Order",
            reference_id=order.id,
            created_by=current_user.id,
        )
        session.add(transaction)

    # 更新訂單狀態
    order.status = OrderStatus.COMPLETED
    order.updated_by = current_user.id

    # 更新客戶消費金額
    if order.customer_id:
        statement = select(Customer).where(Customer.id == order.customer_id)
        result = await session.execute(statement)
        customer = result.scalar_one_or_none()
        if customer:
            customer.total_spending += order.total_amount
            session.add(customer)

    session.add(order)
    await session.commit()

    # 重新查詢以取得包含 items 和 payments 的完整資料
    result = await session.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    order = result.scalar_one()

    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse, summary="取消訂單")
async def cancel_order(order_id: int, session: SessionDep, current_user: CurrentUser):
    """取消訂單"""
    statement = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payments))
        .where(Order.id == order_id)
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
        raise HTTPException(status_code=400, detail="此訂單狀態無法取消")

    order.status = OrderStatus.CANCELLED
    order.updated_by = current_user.id
    session.add(order)
    await session.commit()

    # 重新查詢以取得包含 items 和 payments 的完整資料
    result = await session.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    order = result.scalar_one()

    return order


@router.post("/{order_id}/pay", response_model=MessageResponse, summary="訂單付款")
async def pay_order(
    order_id: int,
    payment_data: PaymentCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """訂單付款"""
    statement = select(Order).where(Order.id == order_id)
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    # 建立付款記錄
    payment = Payment(
        order_id=order.id,
        payment_method=payment_data.payment_method,
        amount=payment_data.amount,
        status=PaymentStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    session.add(payment)
    await session.commit()

    return MessageResponse(message="付款成功")


@router.get("/{order_id}/payments", response_model=list[PaymentResponse], summary="取得訂單付款記錄")
async def get_order_payments(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得訂單的付款記錄"""
    # 檢查訂單是否存在
    order_result = await session.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    # 查詢付款記錄
    statement = select(Payment).where(Payment.order_id == order_id).order_by(Payment.id.desc())
    result = await session.execute(statement)
    payments = result.scalars().all()

    return payments


@router.post("/{order_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, summary="建立付款記錄")
async def create_payment(
    order_id: int,
    payment_data: PaymentCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立訂單付款記錄"""
    statement = select(Order).where(Order.id == order_id)
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="訂單不存在")

    # 建立付款記錄
    payment = Payment(
        order_id=order.id,
        payment_method=payment_data.payment_method,
        amount=payment_data.amount,
        status=PaymentStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    return payment
