"""
庫存盤點管理 API 端點

提供庫存盤點單的 CRUD 與狀態變更功能。
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.stock import StockCount, StockCountItem, StockCountStatus
from app.kamesan.models.store import Warehouse
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.stock import (
    StockCountCreate,
    StockCountItemUpdate,
    StockCountResponse,
    StockCountSummary,
    StockCountUpdate,
)

router = APIRouter()


def generate_count_number() -> str:
    """產生盤點單號"""
    now = datetime.now(timezone.utc)
    return f"SC{now.strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=PaginatedResponse[StockCountSummary], summary="取得盤點單列表")
async def get_stock_counts(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    warehouse_id: Optional[int] = Query(default=None),
    status_filter: Optional[StockCountStatus] = Query(default=None, alias="status"),
):
    """取得盤點單列表"""
    statement = select(StockCount)

    if warehouse_id is not None:
        statement = statement.where(StockCount.warehouse_id == warehouse_id)
    if status_filter is not None:
        statement = statement.where(StockCount.status == status_filter)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(StockCount.id.desc()).options(
        selectinload(StockCount.items)
    )

    result = await session.execute(statement)
    counts = result.scalars().all()

    # 計算摘要資訊
    summaries = []
    for count in counts:
        warehouse_stmt = select(Warehouse).where(Warehouse.id == count.warehouse_id)
        warehouse_result = await session.execute(warehouse_stmt)
        warehouse = warehouse_result.scalar_one_or_none()

        summary = StockCountSummary(
            id=count.id,
            count_number=count.count_number,
            warehouse_id=count.warehouse_id,
            warehouse_name=warehouse.name if warehouse else None,
            count_date=count.count_date,
            status=count.status,
            item_count=count.item_count,
            total_difference=count.total_difference,
            created_at=count.created_at,
        )
        summaries.append(summary)

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.get("/{count_id}", response_model=StockCountResponse, summary="取得盤點單詳情")
async def get_stock_count(
    count_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一盤點單詳情"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    return count


@router.post("", response_model=StockCountResponse, status_code=status.HTTP_201_CREATED, summary="建立盤點單")
async def create_stock_count(
    count_data: StockCountCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的盤點單"""
    # 檢查倉庫是否存在
    warehouse_result = await session.execute(
        select(Warehouse).where(Warehouse.id == count_data.warehouse_id, Warehouse.is_deleted == False)
    )
    if warehouse_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="倉庫不存在")

    # 建立盤點單
    count = StockCount(
        count_number=count_data.count_number or generate_count_number(),
        warehouse_id=count_data.warehouse_id,
        count_date=count_data.count_date or date.today(),
        notes=count_data.notes,
        created_by=current_user.id,
    )

    session.add(count)
    await session.flush()

    # 建立盤點明細
    if count_data.items:
        for item_data in count_data.items:
            item = StockCountItem(
                stock_count_id=count.id,
                product_id=item_data.product_id,
                system_quantity=item_data.system_quantity,
                actual_quantity=item_data.actual_quantity,
                notes=item_data.notes,
            )
            item.calculate_difference()
            session.add(item)

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count


@router.put("/{count_id}", response_model=StockCountResponse, summary="更新盤點單")
async def update_stock_count(
    count_id: int,
    count_data: StockCountUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新盤點單"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status not in (StockCountStatus.DRAFT, StockCountStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail="只能更新草稿或進行中的盤點單")

    update_data = count_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(count, field, value)

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count


@router.delete("/{count_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除盤點單")
async def delete_stock_count(
    count_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除盤點單（只能刪除草稿狀態）"""
    statement = select(StockCount).where(StockCount.id == count_id)
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status != StockCountStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能刪除草稿狀態的盤點單")

    await session.delete(count)
    await session.commit()


@router.post("/{count_id}/start", response_model=StockCountResponse, summary="開始盤點")
async def start_stock_count(
    count_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """開始盤點作業"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status != StockCountStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能開始草稿狀態的盤點單")

    # 自動載入倉庫中的商品庫存
    if not count.items:
        inventory_stmt = select(Inventory).where(Inventory.warehouse_id == count.warehouse_id)
        inventory_result = await session.execute(inventory_stmt)
        inventories = inventory_result.scalars().all()

        for inv in inventories:
            item = StockCountItem(
                stock_count_id=count.id,
                product_id=inv.product_id,
                system_quantity=inv.quantity,
                actual_quantity=0,
            )
            session.add(item)

    count.start()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count


@router.post("/{count_id}/complete", response_model=StockCountResponse, summary="完成盤點")
async def complete_stock_count(
    count_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """完成盤點並更新庫存"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status != StockCountStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="只能完成進行中的盤點單")

    # 更新庫存並建立異動記錄
    for item in count.items:
        if item.difference != 0:
            # 查詢庫存
            inv_stmt = select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == count.warehouse_id,
            )
            inv_result = await session.execute(inv_stmt)
            inventory = inv_result.scalar_one_or_none()

            if inventory:
                before_qty = inventory.quantity
                inventory.quantity = item.actual_quantity

                # 建立庫存異動記錄
                transaction = InventoryTransaction(
                    product_id=item.product_id,
                    warehouse_id=count.warehouse_id,
                    transaction_type=TransactionType.ADJUSTMENT,
                    quantity=item.difference,
                    before_quantity=before_qty,
                    after_quantity=item.actual_quantity,
                    reference_type="StockCount",
                    reference_id=count.id,
                    notes=f"盤點調整: {count.count_number}",
                    created_by=current_user.id,
                )
                session.add(transaction)

    count.complete(current_user.id)
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count


@router.post("/{count_id}/cancel", response_model=StockCountResponse, summary="取消盤點")
async def cancel_stock_count(
    count_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取消盤點單"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status == StockCountStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="無法取消已完成的盤點單")

    count.cancel()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count


@router.put("/{count_id}/items/{item_id}", response_model=StockCountResponse, summary="更新盤點明細")
async def update_stock_count_item(
    count_id: int,
    item_id: int,
    item_data: StockCountItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新盤點明細的實際數量"""
    statement = select(StockCount).where(
        StockCount.id == count_id
    ).options(selectinload(StockCount.items))
    result = await session.execute(statement)
    count = result.scalar_one_or_none()

    if count is None:
        raise HTTPException(status_code=404, detail="找不到盤點單")

    if count.status != StockCountStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="只能更新進行中的盤點單明細")

    # 查詢明細
    item_stmt = select(StockCountItem).where(
        StockCountItem.id == item_id,
        StockCountItem.stock_count_id == count_id,
    )
    item_result = await session.execute(item_stmt)
    item = item_result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="找不到盤點明細")

    if item_data.actual_quantity is not None:
        item.actual_quantity = item_data.actual_quantity
        item.calculate_difference()

    if item_data.notes is not None:
        item.notes = item_data.notes

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.items))
    )
    count = result.scalar_one()

    return count
