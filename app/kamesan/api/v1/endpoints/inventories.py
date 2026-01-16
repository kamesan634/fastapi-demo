"""
庫存管理 API 端點

提供庫存查詢與調整功能。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.product import Product
from app.kamesan.models.store import Warehouse
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.inventory import (
    InventoryAdjustByIdRequest,
    InventoryAdjustRequest,
    InventoryResponse,
    InventoryTransactionResponse,
    LowStockResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[InventoryResponse], summary="取得庫存列表")
async def get_inventories(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    product_id: Optional[int] = Query(default=None),
    warehouse_id: Optional[int] = Query(default=None),
):
    """取得庫存列表"""
    statement = select(Inventory)

    if product_id is not None:
        statement = statement.where(Inventory.product_id == product_id)

    if warehouse_id is not None:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Inventory.id.desc())

    result = await session.execute(statement)
    inventories = result.scalars().all()

    return PaginatedResponse.create(items=inventories, total=total, page=page, page_size=page_size)


@router.get("/low-stock", response_model=list[LowStockResponse], summary="取得低庫存商品")
async def get_low_stock_products(
    session: SessionDep,
    current_user: CurrentUser,
    warehouse_id: Optional[int] = Query(default=None),
):
    """取得低庫存商品列表"""
    statement = (
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(Product.is_deleted == False)
        .where(Inventory.quantity < Product.min_stock)
    )

    if warehouse_id is not None:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)

    result = await session.execute(statement)
    rows = result.all()

    low_stock_items = []
    for inventory, product, warehouse in rows:
        low_stock_items.append(
            LowStockResponse(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                warehouse_id=warehouse.id,
                warehouse_name=warehouse.name,
                current_quantity=inventory.quantity,
                min_stock=product.min_stock,
                shortage=product.min_stock - inventory.quantity,
            )
        )

    return low_stock_items


@router.get("/{inventory_id}", response_model=InventoryResponse, summary="取得單一庫存")
async def get_inventory(
    inventory_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一庫存記錄"""
    statement = select(Inventory).where(Inventory.id == inventory_id)
    result = await session.execute(statement)
    inventory = result.scalar_one_or_none()

    if inventory is None:
        raise HTTPException(status_code=404, detail="找不到庫存記錄")

    return inventory


@router.post("/adjust", response_model=InventoryResponse, summary="調整庫存")
async def adjust_inventory(
    adjust_data: InventoryAdjustRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """調整庫存數量"""
    # 查詢庫存記錄
    statement = select(Inventory).where(
        Inventory.product_id == adjust_data.product_id,
        Inventory.warehouse_id == adjust_data.warehouse_id,
    )
    result = await session.execute(statement)
    inventory = result.scalar_one_or_none()

    # 如果庫存記錄不存在，建立新的
    if inventory is None:
        if adjust_data.quantity < 0:
            raise HTTPException(status_code=400, detail="庫存不足")

        inventory = Inventory(
            product_id=adjust_data.product_id,
            warehouse_id=adjust_data.warehouse_id,
            quantity=adjust_data.quantity,
        )
        before_quantity = 0
    else:
        before_quantity = inventory.quantity
        new_quantity = inventory.quantity + adjust_data.quantity

        if new_quantity < 0:
            raise HTTPException(status_code=400, detail="庫存不足")

        inventory.quantity = new_quantity

    session.add(inventory)

    # 建立異動記錄
    transaction = InventoryTransaction(
        product_id=adjust_data.product_id,
        warehouse_id=adjust_data.warehouse_id,
        transaction_type=TransactionType.ADJUSTMENT,
        quantity=adjust_data.quantity,
        before_quantity=before_quantity,
        after_quantity=inventory.quantity,
        notes=adjust_data.reason,
        created_by=current_user.id,
    )
    session.add(transaction)

    await session.commit()
    await session.refresh(inventory)

    return inventory


@router.post("/{inventory_id}/adjust", response_model=InventoryResponse, summary="依 ID 調整庫存")
async def adjust_inventory_by_id(
    inventory_id: int,
    adjust_data: InventoryAdjustByIdRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """依庫存 ID 調整庫存數量"""
    # 查詢庫存記錄
    statement = select(Inventory).where(Inventory.id == inventory_id)
    result = await session.execute(statement)
    inventory = result.scalar_one_or_none()

    if inventory is None:
        raise HTTPException(status_code=404, detail="找不到庫存記錄")

    before_quantity = inventory.quantity
    new_quantity = inventory.quantity + adjust_data.quantity

    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="庫存不足")

    inventory.quantity = new_quantity
    session.add(inventory)

    # 建立異動記錄
    transaction = InventoryTransaction(
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        transaction_type=TransactionType.ADJUSTMENT,
        quantity=adjust_data.quantity,
        before_quantity=before_quantity,
        after_quantity=inventory.quantity,
        notes=adjust_data.reason,
        created_by=current_user.id,
    )
    session.add(transaction)

    await session.commit()
    await session.refresh(inventory)

    return inventory


@router.get("/transactions", response_model=PaginatedResponse[InventoryTransactionResponse], summary="取得庫存異動記錄")
async def get_inventory_transactions(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    product_id: Optional[int] = Query(default=None),
    warehouse_id: Optional[int] = Query(default=None),
    transaction_type: Optional[TransactionType] = Query(default=None),
):
    """取得庫存異動記錄"""
    statement = select(InventoryTransaction)

    if product_id is not None:
        statement = statement.where(InventoryTransaction.product_id == product_id)

    if warehouse_id is not None:
        statement = statement.where(InventoryTransaction.warehouse_id == warehouse_id)

    if transaction_type is not None:
        statement = statement.where(InventoryTransaction.transaction_type == transaction_type)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(InventoryTransaction.id.desc())

    result = await session.execute(statement)
    transactions = result.scalars().all()

    return PaginatedResponse.create(items=transactions, total=total, page=page, page_size=page_size)
