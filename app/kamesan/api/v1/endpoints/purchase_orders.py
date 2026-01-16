"""
採購單管理 API 端點

提供採購單的 CRUD 與狀態變更功能。
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.product import Product
from app.kamesan.models.purchase import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.kamesan.models.store import Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.purchase import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderSummary,
    PurchaseOrderUpdate,
)

router = APIRouter()


def generate_order_number() -> str:
    """產生採購單號"""
    now = datetime.now(timezone.utc)
    return f"PO{now.strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=PaginatedResponse[PurchaseOrderSummary], summary="取得採購單列表")
async def get_purchase_orders(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    supplier_id: Optional[int] = Query(default=None),
    warehouse_id: Optional[int] = Query(default=None),
    status_filter: Optional[PurchaseOrderStatus] = Query(default=None, alias="status"),
):
    """取得採購單列表"""
    statement = select(PurchaseOrder).where(PurchaseOrder.is_deleted == False)

    if supplier_id is not None:
        statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id is not None:
        statement = statement.where(PurchaseOrder.warehouse_id == warehouse_id)
    if status_filter is not None:
        statement = statement.where(PurchaseOrder.status == status_filter)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    # 需要 eager load items 以便計算 item_count
    statement = statement.options(
        selectinload(PurchaseOrder.items)
    ).offset(offset).limit(page_size).order_by(PurchaseOrder.id.desc())

    result = await session.execute(statement)
    orders = result.scalars().all()

    # 計算摘要資訊
    summaries = []
    for order in orders:
        # 查詢供應商和倉庫名稱
        supplier_stmt = select(Supplier).where(Supplier.id == order.supplier_id)
        warehouse_stmt = select(Warehouse).where(Warehouse.id == order.warehouse_id)

        supplier_result = await session.execute(supplier_stmt)
        warehouse_result = await session.execute(warehouse_stmt)

        supplier = supplier_result.scalar_one_or_none()
        warehouse = warehouse_result.scalar_one_or_none()

        summary = PurchaseOrderSummary(
            id=order.id,
            order_number=order.order_number,
            supplier_id=order.supplier_id,
            supplier_name=supplier.name if supplier else None,
            warehouse_id=order.warehouse_id,
            warehouse_name=warehouse.name if warehouse else None,
            order_date=order.order_date,
            expected_date=order.expected_date,
            status=order.status,
            total_amount=order.total_amount,
            item_count=order.item_count,
            created_at=order.created_at,
        )
        summaries.append(summary)

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=PurchaseOrderResponse, summary="取得採購單詳情")
async def get_purchase_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一採購單詳情"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    ).options(selectinload(PurchaseOrder.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    return order


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED, summary="建立採購單")
async def create_purchase_order(
    order_data: PurchaseOrderCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的採購單"""
    # 檢查供應商
    supplier_result = await session.execute(
        select(Supplier).where(Supplier.id == order_data.supplier_id, Supplier.is_deleted == False)
    )
    if supplier_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="供應商不存在")

    # 檢查倉庫
    warehouse_result = await session.execute(
        select(Warehouse).where(Warehouse.id == order_data.warehouse_id, Warehouse.is_deleted == False)
    )
    if warehouse_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="倉庫不存在")

    # 建立採購單
    order = PurchaseOrder(
        order_number=order_data.order_number or generate_order_number(),
        supplier_id=order_data.supplier_id,
        warehouse_id=order_data.warehouse_id,
        order_date=order_data.order_date or date.today(),
        expected_date=order_data.expected_date,
        notes=order_data.notes,
        created_by=current_user.id,
    )

    session.add(order)
    await session.flush()

    # 建立採購明細
    total_amount = 0
    for item_data in order_data.items:
        # 檢查商品
        product_result = await session.execute(
            select(Product).where(Product.id == item_data.product_id, Product.is_deleted == False)
        )
        if product_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"商品 ID {item_data.product_id} 不存在")

        item = PurchaseOrderItem(
            purchase_order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            notes=item_data.notes,
        )
        session.add(item)
        total_amount += item_data.unit_price * item_data.quantity

    order.total_amount = total_amount

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.items))
    )
    order = result.scalar_one()

    return order


@router.put("/{order_id}", response_model=PurchaseOrderResponse, summary="更新採購單")
async def update_purchase_order(
    order_id: int,
    order_data: PurchaseOrderUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新採購單"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    ).options(selectinload(PurchaseOrder.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    if order.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING):
        raise HTTPException(status_code=400, detail="只能更新草稿或待審核的採購單")

    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    order.updated_by = current_user.id

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.items))
    )
    order = result.scalar_one()

    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除採購單")
async def delete_purchase_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除採購單（軟刪除，只能刪除草稿狀態）"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    if order.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能刪除草稿狀態的採購單")

    order.is_deleted = True
    order.updated_by = current_user.id

    await session.commit()


@router.post("/{order_id}/submit", response_model=PurchaseOrderResponse, summary="提交採購單")
async def submit_purchase_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """提交採購單待審核"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    ).options(selectinload(PurchaseOrder.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    if order.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能提交草稿狀態的採購單")

    order.submit()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.items))
    )
    order = result.scalar_one()

    return order


@router.post("/{order_id}/approve", response_model=PurchaseOrderResponse, summary="核准採購單")
async def approve_purchase_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """核准採購單"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    ).options(selectinload(PurchaseOrder.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    if order.status != PurchaseOrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能核准待審核的採購單")

    order.approve(current_user.id)
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.items))
    )
    order = result.scalar_one()

    return order


@router.post("/{order_id}/cancel", response_model=PurchaseOrderResponse, summary="取消採購單")
async def cancel_purchase_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取消採購單"""
    statement = select(PurchaseOrder).where(
        PurchaseOrder.id == order_id,
        PurchaseOrder.is_deleted == False,
    ).options(selectinload(PurchaseOrder.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="找不到採購單")

    if order.status in (PurchaseOrderStatus.COMPLETED, PurchaseOrderStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="無法取消已完成或已取消的採購單")

    order.cancel()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.items))
    )
    order = result.scalar_one()

    return order
