"""
驗收單管理 API 端點

提供驗收單的 CRUD 與狀態變更功能。
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.product import Product
from app.kamesan.models.purchase import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    PurchaseReceipt,
    PurchaseReceiptItem,
    PurchaseReceiptStatus,
)
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.purchase import (
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
    PurchaseReceiptSummary,
)

router = APIRouter()


def generate_receipt_number() -> str:
    """產生驗收單號"""
    now = datetime.now(timezone.utc)
    return f"PR{now.strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=PaginatedResponse[PurchaseReceiptSummary], summary="取得驗收單列表")
async def get_purchase_receipts(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    purchase_order_id: Optional[int] = Query(default=None),
    status_filter: Optional[PurchaseReceiptStatus] = Query(default=None, alias="status"),
):
    """取得驗收單列表"""
    statement = select(PurchaseReceipt)

    if purchase_order_id is not None:
        statement = statement.where(PurchaseReceipt.purchase_order_id == purchase_order_id)
    if status_filter is not None:
        statement = statement.where(PurchaseReceipt.status == status_filter)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(PurchaseReceipt.id.desc())

    result = await session.execute(statement)
    receipts = result.scalars().all()

    # 計算摘要資訊
    summaries = []
    for receipt in receipts:
        # 查詢採購單號
        po_stmt = select(PurchaseOrder).where(PurchaseOrder.id == receipt.purchase_order_id)
        po_result = await session.execute(po_stmt)
        po = po_result.scalar_one_or_none()

        summary = PurchaseReceiptSummary(
            id=receipt.id,
            receipt_number=receipt.receipt_number,
            purchase_order_id=receipt.purchase_order_id,
            purchase_order_number=po.order_number if po else None,
            receipt_date=receipt.receipt_date,
            status=receipt.status,
            total_quantity=receipt.total_quantity,
            created_at=receipt.created_at,
        )
        summaries.append(summary)

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.get("/{receipt_id}", response_model=PurchaseReceiptResponse, summary="取得驗收單詳情")
async def get_purchase_receipt(
    receipt_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一驗收單詳情"""
    statement = select(PurchaseReceipt).where(
        PurchaseReceipt.id == receipt_id
    ).options(selectinload(PurchaseReceipt.items))
    result = await session.execute(statement)
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise HTTPException(status_code=404, detail="找不到驗收單")

    return receipt


@router.post("", response_model=PurchaseReceiptResponse, status_code=status.HTTP_201_CREATED, summary="建立驗收單")
async def create_purchase_receipt(
    receipt_data: PurchaseReceiptCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的驗收單"""
    # 檢查採購單
    po_result = await session.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == receipt_data.purchase_order_id,
            PurchaseOrder.is_deleted == False,
        )
    )
    purchase_order = po_result.scalar_one_or_none()
    if purchase_order is None:
        raise HTTPException(status_code=400, detail="採購單不存在")

    if purchase_order.status not in (PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIAL):
        raise HTTPException(status_code=400, detail="只能對已核准或部分收貨的採購單建立驗收單")

    # 建立驗收單
    receipt = PurchaseReceipt(
        receipt_number=receipt_data.receipt_number or generate_receipt_number(),
        purchase_order_id=receipt_data.purchase_order_id,
        receipt_date=receipt_data.receipt_date or date.today(),
        notes=receipt_data.notes,
        created_by=current_user.id,
    )

    session.add(receipt)
    await session.flush()

    # 建立驗收明細
    for item_data in receipt_data.items:
        # 檢查商品
        product_result = await session.execute(
            select(Product).where(Product.id == item_data.product_id, Product.is_deleted == False)
        )
        if product_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"商品 ID {item_data.product_id} 不存在")

        item = PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            product_id=item_data.product_id,
            purchase_order_item_id=item_data.purchase_order_item_id,
            received_quantity=item_data.received_quantity,
            rejected_quantity=item_data.rejected_quantity,
            notes=item_data.notes,
        )
        session.add(item)

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReceipt)
        .where(PurchaseReceipt.id == receipt.id)
        .options(selectinload(PurchaseReceipt.items))
    )
    receipt = result.scalar_one()

    return receipt


@router.post("/{receipt_id}/complete", response_model=PurchaseReceiptResponse, summary="完成驗收")
async def complete_purchase_receipt(
    receipt_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """完成驗收並更新庫存"""
    statement = select(PurchaseReceipt).where(
        PurchaseReceipt.id == receipt_id
    ).options(selectinload(PurchaseReceipt.items))
    result = await session.execute(statement)
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise HTTPException(status_code=404, detail="找不到驗收單")

    if receipt.status != PurchaseReceiptStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能完成待驗收的驗收單")

    # 取得採購單（需要 eager load items 以便後續檢查收貨狀態）
    po_result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == receipt.purchase_order_id)
        .options(selectinload(PurchaseOrder.items))
    )
    purchase_order = po_result.scalar_one_or_none()

    if purchase_order is None:
        raise HTTPException(status_code=400, detail="找不到關聯的採購單")

    # 更新庫存並建立異動記錄
    for item in receipt.items:
        if item.received_quantity > 0:
            # 查詢庫存
            inv_stmt = select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == purchase_order.warehouse_id,
            )
            inv_result = await session.execute(inv_stmt)
            inventory = inv_result.scalar_one_or_none()

            if inventory is None:
                # 建立新的庫存記錄
                inventory = Inventory(
                    product_id=item.product_id,
                    warehouse_id=purchase_order.warehouse_id,
                    quantity=item.received_quantity,
                )
                session.add(inventory)
                before_qty = 0
            else:
                before_qty = inventory.quantity
                inventory.quantity += item.received_quantity

            # 建立庫存異動記錄
            transaction = InventoryTransaction(
                product_id=item.product_id,
                warehouse_id=purchase_order.warehouse_id,
                transaction_type=TransactionType.PURCHASE,
                quantity=item.received_quantity,
                before_quantity=before_qty,
                after_quantity=inventory.quantity if inventory else item.received_quantity,
                reference_type="PurchaseReceipt",
                reference_id=receipt.id,
                notes=f"採購入庫: {receipt.receipt_number}",
                created_by=current_user.id,
            )
            session.add(transaction)

            # 更新採購單明細的已收貨數量
            if item.purchase_order_item_id:
                po_item_stmt = select(PurchaseOrderItem).where(
                    PurchaseOrderItem.id == item.purchase_order_item_id
                )
                po_item_result = await session.execute(po_item_stmt)
                po_item = po_item_result.scalar_one_or_none()
                if po_item:
                    po_item.received_quantity += item.received_quantity

    # 完成驗收單
    receipt.complete(current_user.id)

    # 檢查採購單是否全部收貨完成
    all_received = True
    for po_item in purchase_order.items:
        if po_item.received_quantity < po_item.quantity:
            all_received = False
            break

    if all_received:
        purchase_order.status = PurchaseOrderStatus.COMPLETED
    else:
        purchase_order.status = PurchaseOrderStatus.PARTIAL

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReceipt)
        .where(PurchaseReceipt.id == receipt.id)
        .options(selectinload(PurchaseReceipt.items))
    )
    receipt = result.scalar_one()

    return receipt


@router.post("/{receipt_id}/cancel", response_model=PurchaseReceiptResponse, summary="取消驗收單")
async def cancel_purchase_receipt(
    receipt_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取消驗收單"""
    statement = select(PurchaseReceipt).where(
        PurchaseReceipt.id == receipt_id
    ).options(selectinload(PurchaseReceipt.items))
    result = await session.execute(statement)
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise HTTPException(status_code=404, detail="找不到驗收單")

    if receipt.status != PurchaseReceiptStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能取消待驗收的驗收單")

    receipt.cancel()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReceipt)
        .where(PurchaseReceipt.id == receipt.id)
        .options(selectinload(PurchaseReceipt.items))
    )
    receipt = result.scalar_one()

    return receipt
