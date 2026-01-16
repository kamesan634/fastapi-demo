"""
庫存調撥管理 API 端點

提供庫存調撥單的 CRUD 與狀態變更功能。
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.stock import StockTransfer, StockTransferItem, StockTransferStatus
from app.kamesan.models.store import Warehouse
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.stock import (
    StockTransferCreate,
    StockTransferResponse,
    StockTransferSummary,
    StockTransferUpdate,
)

router = APIRouter()


def generate_transfer_number() -> str:
    """產生調撥單號"""
    now = datetime.now(timezone.utc)
    return f"ST{now.strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=PaginatedResponse[StockTransferSummary], summary="取得調撥單列表")
async def get_stock_transfers(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_warehouse_id: Optional[int] = Query(default=None),
    destination_warehouse_id: Optional[int] = Query(default=None),
    status_filter: Optional[StockTransferStatus] = Query(default=None, alias="status"),
):
    """取得調撥單列表"""
    statement = select(StockTransfer)

    if source_warehouse_id is not None:
        statement = statement.where(StockTransfer.source_warehouse_id == source_warehouse_id)
    if destination_warehouse_id is not None:
        statement = statement.where(StockTransfer.destination_warehouse_id == destination_warehouse_id)
    if status_filter is not None:
        statement = statement.where(StockTransfer.status == status_filter)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(StockTransfer.id.desc()).options(
        selectinload(StockTransfer.items)
    )

    result = await session.execute(statement)
    transfers = result.scalars().all()

    # 計算摘要資訊
    summaries = []
    for transfer in transfers:
        # 查詢倉庫名稱
        src_stmt = select(Warehouse).where(Warehouse.id == transfer.source_warehouse_id)
        dst_stmt = select(Warehouse).where(Warehouse.id == transfer.destination_warehouse_id)

        src_result = await session.execute(src_stmt)
        dst_result = await session.execute(dst_stmt)

        src_warehouse = src_result.scalar_one_or_none()
        dst_warehouse = dst_result.scalar_one_or_none()

        summary = StockTransferSummary(
            id=transfer.id,
            transfer_number=transfer.transfer_number,
            source_warehouse_id=transfer.source_warehouse_id,
            source_warehouse_name=src_warehouse.name if src_warehouse else None,
            destination_warehouse_id=transfer.destination_warehouse_id,
            destination_warehouse_name=dst_warehouse.name if dst_warehouse else None,
            transfer_date=transfer.transfer_date,
            status=transfer.status,
            item_count=transfer.item_count,
            total_quantity=transfer.total_quantity,
            created_at=transfer.created_at,
        )
        summaries.append(summary)

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.get("/{transfer_id}", response_model=StockTransferResponse, summary="取得調撥單詳情")
async def get_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一調撥單詳情"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    return transfer


@router.post("", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED, summary="建立調撥單")
async def create_stock_transfer(
    transfer_data: StockTransferCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的調撥單"""
    # 檢查來源倉庫
    src_result = await session.execute(
        select(Warehouse).where(
            Warehouse.id == transfer_data.source_warehouse_id,
            Warehouse.is_deleted == False,
        )
    )
    if src_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="來源倉庫不存在")

    # 檢查目的倉庫
    dst_result = await session.execute(
        select(Warehouse).where(
            Warehouse.id == transfer_data.destination_warehouse_id,
            Warehouse.is_deleted == False,
        )
    )
    if dst_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="目的倉庫不存在")

    # 建立調撥單
    transfer = StockTransfer(
        transfer_number=transfer_data.transfer_number or generate_transfer_number(),
        source_warehouse_id=transfer_data.source_warehouse_id,
        destination_warehouse_id=transfer_data.destination_warehouse_id,
        transfer_date=transfer_data.transfer_date or date.today(),
        expected_date=transfer_data.expected_date,
        notes=transfer_data.notes,
        created_by=current_user.id,
    )

    session.add(transfer)
    await session.flush()

    # 建立調撥明細
    for item_data in transfer_data.items:
        item = StockTransferItem(
            stock_transfer_id=transfer.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            notes=item_data.notes,
        )
        session.add(item)

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.put("/{transfer_id}", response_model=StockTransferResponse, summary="更新調撥單")
async def update_stock_transfer(
    transfer_id: int,
    transfer_data: StockTransferUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新調撥單"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status not in (StockTransferStatus.DRAFT, StockTransferStatus.PENDING):
        raise HTTPException(status_code=400, detail="只能更新草稿或待審核的調撥單")

    update_data = transfer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transfer, field, value)

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除調撥單")
async def delete_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除調撥單（只能刪除草稿狀態）"""
    statement = select(StockTransfer).where(StockTransfer.id == transfer_id)
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status != StockTransferStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能刪除草稿狀態的調撥單")

    await session.delete(transfer)
    await session.commit()


@router.post("/{transfer_id}/submit", response_model=StockTransferResponse, summary="提交調撥單")
async def submit_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """提交調撥單待審核"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status != StockTransferStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能提交草稿狀態的調撥單")

    transfer.submit()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.post("/{transfer_id}/approve", response_model=StockTransferResponse, summary="核准調撥單")
async def approve_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """核准調撥單"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status != StockTransferStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能核准待審核的調撥單")

    transfer.approve(current_user.id)
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.post("/{transfer_id}/ship", response_model=StockTransferResponse, summary="出貨")
async def ship_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """調撥出貨（從來源倉庫扣除庫存）"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status != StockTransferStatus.APPROVED:
        raise HTTPException(status_code=400, detail="只能對已核准的調撥單出貨")

    # 扣除來源倉庫庫存
    for item in transfer.items:
        inv_stmt = select(Inventory).where(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == transfer.source_warehouse_id,
        )
        inv_result = await session.execute(inv_stmt)
        inventory = inv_result.scalar_one_or_none()

        if inventory is None or inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=400, detail=f"商品 ID {item.product_id} 庫存不足"
            )

        before_qty = inventory.quantity
        inventory.quantity -= item.quantity

        # 建立庫存異動記錄
        transaction = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=transfer.source_warehouse_id,
            transaction_type=TransactionType.TRANSFER_OUT,
            quantity=-item.quantity,
            before_quantity=before_qty,
            after_quantity=inventory.quantity,
            reference_type="StockTransfer",
            reference_id=transfer.id,
            notes=f"調撥出庫: {transfer.transfer_number}",
            created_by=current_user.id,
        )
        session.add(transaction)

    transfer.ship()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.post("/{transfer_id}/receive", response_model=StockTransferResponse, summary="收貨")
async def receive_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """調撥收貨（增加目的倉庫庫存）"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status != StockTransferStatus.IN_TRANSIT:
        raise HTTPException(status_code=400, detail="只能對運送中的調撥單收貨")

    # 增加目的倉庫庫存
    for item in transfer.items:
        inv_stmt = select(Inventory).where(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == transfer.destination_warehouse_id,
        )
        inv_result = await session.execute(inv_stmt)
        inventory = inv_result.scalar_one_or_none()

        received_qty = item.received_quantity if item.received_quantity is not None else item.quantity

        if inventory is None:
            # 建立新的庫存記錄
            inventory = Inventory(
                product_id=item.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                quantity=received_qty,
            )
            session.add(inventory)
            before_qty = 0
        else:
            before_qty = inventory.quantity
            inventory.quantity += received_qty

        # 更新明細收貨數量
        item.received_quantity = received_qty

        # 建立庫存異動記錄
        transaction = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=transfer.destination_warehouse_id,
            transaction_type=TransactionType.TRANSFER_IN,
            quantity=received_qty,
            before_quantity=before_qty,
            after_quantity=inventory.quantity if inventory else received_qty,
            reference_type="StockTransfer",
            reference_id=transfer.id,
            notes=f"調撥入庫: {transfer.transfer_number}",
            created_by=current_user.id,
        )
        session.add(transaction)

    transfer.receive(current_user.id)
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer


@router.post("/{transfer_id}/cancel", response_model=StockTransferResponse, summary="取消調撥單")
async def cancel_stock_transfer(
    transfer_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取消調撥單"""
    statement = select(StockTransfer).where(
        StockTransfer.id == transfer_id
    ).options(selectinload(StockTransfer.items))
    result = await session.execute(statement)
    transfer = result.scalar_one_or_none()

    if transfer is None:
        raise HTTPException(status_code=404, detail="找不到調撥單")

    if transfer.status in (StockTransferStatus.IN_TRANSIT, StockTransferStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="無法取消已出貨或已完成的調撥單")

    transfer.cancel()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockTransfer)
        .where(StockTransfer.id == transfer.id)
        .options(selectinload(StockTransfer.items))
    )
    transfer = result.scalar_one()

    return transfer
