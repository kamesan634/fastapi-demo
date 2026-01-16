"""
退貨單管理 API 端點

提供退貨單的 CRUD 與狀態變更功能。
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
    PurchaseReturn,
    PurchaseReturnItem,
    PurchaseReturnStatus,
)
from app.kamesan.models.store import Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.purchase import (
    PurchaseReturnCreate,
    PurchaseReturnResponse,
    PurchaseReturnSummary,
    PurchaseReturnUpdate,
)

router = APIRouter()


def generate_return_number() -> str:
    """產生退貨單號"""
    now = datetime.now(timezone.utc)
    return f"RT{now.strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=PaginatedResponse[PurchaseReturnSummary], summary="取得退貨單列表")
async def get_purchase_returns(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    supplier_id: Optional[int] = Query(default=None),
    warehouse_id: Optional[int] = Query(default=None),
    status_filter: Optional[PurchaseReturnStatus] = Query(default=None, alias="status"),
):
    """取得退貨單列表"""
    statement = select(PurchaseReturn)

    if supplier_id is not None:
        statement = statement.where(PurchaseReturn.supplier_id == supplier_id)
    if warehouse_id is not None:
        statement = statement.where(PurchaseReturn.warehouse_id == warehouse_id)
    if status_filter is not None:
        statement = statement.where(PurchaseReturn.status == status_filter)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(PurchaseReturn.id.desc())

    result = await session.execute(statement)
    returns = result.scalars().all()

    # 計算摘要資訊
    summaries = []
    for ret in returns:
        # 查詢供應商和倉庫名稱
        supplier_stmt = select(Supplier).where(Supplier.id == ret.supplier_id)
        warehouse_stmt = select(Warehouse).where(Warehouse.id == ret.warehouse_id)

        supplier_result = await session.execute(supplier_stmt)
        warehouse_result = await session.execute(warehouse_stmt)

        supplier = supplier_result.scalar_one_or_none()
        warehouse = warehouse_result.scalar_one_or_none()

        summary = PurchaseReturnSummary(
            id=ret.id,
            return_number=ret.return_number,
            supplier_id=ret.supplier_id,
            supplier_name=supplier.name if supplier else None,
            warehouse_id=ret.warehouse_id,
            warehouse_name=warehouse.name if warehouse else None,
            return_date=ret.return_date,
            status=ret.status,
            total_amount=ret.total_amount,
            item_count=ret.item_count,
            created_at=ret.created_at,
        )
        summaries.append(summary)

    return PaginatedResponse.create(items=summaries, total=total, page=page, page_size=page_size)


@router.get("/{return_id}", response_model=PurchaseReturnResponse, summary="取得退貨單詳情")
async def get_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一退貨單詳情"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    return ret


@router.post("", response_model=PurchaseReturnResponse, status_code=status.HTTP_201_CREATED, summary="建立退貨單")
async def create_purchase_return(
    return_data: PurchaseReturnCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的退貨單"""
    # 檢查供應商
    supplier_result = await session.execute(
        select(Supplier).where(Supplier.id == return_data.supplier_id, Supplier.is_deleted == False)
    )
    if supplier_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="供應商不存在")

    # 檢查倉庫
    warehouse_result = await session.execute(
        select(Warehouse).where(Warehouse.id == return_data.warehouse_id, Warehouse.is_deleted == False)
    )
    if warehouse_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="倉庫不存在")

    # 建立退貨單
    ret = PurchaseReturn(
        return_number=return_data.return_number or generate_return_number(),
        supplier_id=return_data.supplier_id,
        warehouse_id=return_data.warehouse_id,
        purchase_order_id=return_data.purchase_order_id,
        return_date=return_data.return_date or date.today(),
        reason=return_data.reason,
        notes=return_data.notes,
        created_by=current_user.id,
    )

    session.add(ret)
    await session.flush()

    # 建立退貨明細
    total_amount = 0
    for item_data in return_data.items:
        # 檢查商品
        product_result = await session.execute(
            select(Product).where(Product.id == item_data.product_id, Product.is_deleted == False)
        )
        if product_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"商品 ID {item_data.product_id} 不存在")

        item = PurchaseReturnItem(
            purchase_return_id=ret.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            reason=item_data.reason,
            notes=item_data.notes,
        )
        session.add(item)
        total_amount += item_data.unit_price * item_data.quantity

    ret.total_amount = total_amount

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret


@router.put("/{return_id}", response_model=PurchaseReturnResponse, summary="更新退貨單")
async def update_purchase_return(
    return_id: int,
    return_data: PurchaseReturnUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新退貨單"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status not in (PurchaseReturnStatus.DRAFT, PurchaseReturnStatus.PENDING):
        raise HTTPException(status_code=400, detail="只能更新草稿或待審核的退貨單")

    update_data = return_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ret, field, value)

    ret.updated_by = current_user.id

    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret


@router.delete("/{return_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除退貨單")
async def delete_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除退貨單（只能刪除草稿狀態）"""
    statement = select(PurchaseReturn).where(PurchaseReturn.id == return_id)
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status != PurchaseReturnStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能刪除草稿狀態的退貨單")

    await session.delete(ret)
    await session.commit()


@router.post("/{return_id}/submit", response_model=PurchaseReturnResponse, summary="提交退貨單")
async def submit_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """提交退貨單待審核"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status != PurchaseReturnStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能提交草稿狀態的退貨單")

    ret.submit()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret


@router.post("/{return_id}/approve", response_model=PurchaseReturnResponse, summary="核准退貨單")
async def approve_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """核准退貨單"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status != PurchaseReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能核准待審核的退貨單")

    ret.approve(current_user.id)
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret


@router.post("/{return_id}/complete", response_model=PurchaseReturnResponse, summary="完成退貨")
async def complete_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """完成退貨並更新庫存"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status != PurchaseReturnStatus.APPROVED:
        raise HTTPException(status_code=400, detail="只能完成已核准的退貨單")

    # 扣除庫存並建立異動記錄
    for item in ret.items:
        # 查詢庫存
        inv_stmt = select(Inventory).where(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == ret.warehouse_id,
        )
        inv_result = await session.execute(inv_stmt)
        inventory = inv_result.scalar_one_or_none()

        if inventory is None or inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"商品 ID {item.product_id} 庫存不足，無法退貨",
            )

        before_qty = inventory.quantity
        inventory.quantity -= item.quantity

        # 建立庫存異動記錄
        transaction = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=ret.warehouse_id,
            transaction_type=TransactionType.RETURN,
            quantity=-item.quantity,
            before_quantity=before_qty,
            after_quantity=inventory.quantity,
            reference_type="PurchaseReturn",
            reference_id=ret.id,
            notes=f"採購退貨: {ret.return_number}",
            created_by=current_user.id,
        )
        session.add(transaction)

    ret.complete()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret


@router.post("/{return_id}/cancel", response_model=PurchaseReturnResponse, summary="取消退貨單")
async def cancel_purchase_return(
    return_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取消退貨單"""
    statement = select(PurchaseReturn).where(
        PurchaseReturn.id == return_id
    ).options(selectinload(PurchaseReturn.items))
    result = await session.execute(statement)
    ret = result.scalar_one_or_none()

    if ret is None:
        raise HTTPException(status_code=404, detail="找不到退貨單")

    if ret.status in (PurchaseReturnStatus.COMPLETED, PurchaseReturnStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="無法取消已完成或已取消的退貨單")

    ret.cancel()
    await session.commit()

    # 重新查詢以取得包含 items 的完整資料
    result = await session.execute(
        select(PurchaseReturn)
        .where(PurchaseReturn.id == ret.id)
        .options(selectinload(PurchaseReturn.items))
    )
    ret = result.scalar_one()

    return ret
