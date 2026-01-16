"""
採購建議 API 端點

提供採購建議的產生與轉採購單功能。
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory
from app.kamesan.models.order import Order, OrderItem, OrderStatus
from app.kamesan.models.product import Category, Product
from app.kamesan.models.purchase import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    SupplierPrice,
)
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.purchase_suggestion import (
    ConvertToOrderRequest,
    ConvertToOrderResponse,
    PurchaseSuggestionItem,
    PurchaseSuggestionRequest,
    PurchaseSuggestionResponse,
    PurchaseSuggestionSummary,
    SuggestionMethod,
)
from app.kamesan.services.numbering import NumberingService
from app.kamesan.models.settings import DocumentType

router = APIRouter()


async def _get_product_sales_forecast(
    session: SessionDep,
    product_id: int,
    days: int,
) -> int:
    """
    計算商品的預估銷售量

    根據過去同樣天數的銷售記錄計算日均銷售量，
    再乘以預估天數得到預估銷售量。
    """
    # 計算參考期間
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    # 查詢過去 N 天的銷售數量
    statement = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order)
        .where(
            OrderItem.product_id == product_id,
            Order.status == OrderStatus.COMPLETED,
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
        )
    )
    result = await session.execute(statement)
    total_sales = result.scalar() or 0

    # 計算預估銷售量（使用過去實際銷售的平均值）
    return int(total_sales)


async def _get_in_transit_quantity(
    session: SessionDep,
    product_id: int,
) -> int:
    """
    計算商品的在途庫存數量

    在途庫存 = 已核准但尚未完成入庫的採購單數量
    """
    statement = (
        select(func.coalesce(func.sum(PurchaseOrderItem.quantity - PurchaseOrderItem.received_quantity), 0))
        .join(PurchaseOrder)
        .where(
            PurchaseOrderItem.product_id == product_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.PARTIAL,
            ]),
        )
    )
    result = await session.execute(statement)
    return result.scalar() or 0


async def _get_current_stock(
    session: SessionDep,
    product_id: int,
    warehouse_id: Optional[int] = None,
) -> int:
    """取得商品目前庫存量"""
    statement = select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
        Inventory.product_id == product_id
    )
    if warehouse_id:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)

    result = await session.execute(statement)
    return result.scalar() or 0


async def _get_supplier_price(
    session: SessionDep,
    product_id: int,
    supplier_id: Optional[int] = None,
) -> tuple[Optional[int], Decimal, int]:
    """
    取得供應商報價

    回傳: (supplier_id, unit_price, min_order_quantity)
    """
    statement = select(SupplierPrice).where(
        SupplierPrice.product_id == product_id,
        SupplierPrice.is_active == True,
    )
    if supplier_id:
        statement = statement.where(SupplierPrice.supplier_id == supplier_id)

    statement = statement.order_by(SupplierPrice.unit_price)
    result = await session.execute(statement)
    price = result.scalars().first()

    if price:
        return price.supplier_id, price.unit_price, price.min_order_quantity

    # 如果沒有供應商報價，使用商品成本價
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        return product.supplier_id, product.cost_price, 1

    return None, Decimal("0"), 1


async def _calculate_suggested_quantity(
    safety_stock: int,
    forecast_sales: int,
    current_stock: int,
    in_transit: int,
    min_order_quantity: int,
) -> int:
    """
    計算建議採購數量

    公式: 建議採購量 = 安全庫存 + 預估銷售量 - 現有庫存 - 在途庫存
    最終數量會調整為最小訂購量的整數倍
    """
    raw_quantity = safety_stock + forecast_sales - current_stock - in_transit

    if raw_quantity <= 0:
        return 0

    # 調整為最小訂購量的整數倍
    if min_order_quantity > 1:
        remainder = raw_quantity % min_order_quantity
        if remainder > 0:
            raw_quantity = raw_quantity + (min_order_quantity - remainder)

    return raw_quantity


@router.post(
    "/generate",
    response_model=PurchaseSuggestionResponse,
    summary="產生採購建議",
)
async def generate_suggestions(
    request: PurchaseSuggestionRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依據庫存狀況自動產生採購建議

    計算邏輯:
    建議採購量 = 安全庫存 + 預估銷售量 - 現有庫存 - 在途庫存

    支援的計算方式:
    - LOW_STOCK: 所有低於安全庫存的商品
    - BY_PRODUCT: 指定商品
    - BY_CATEGORY: 指定類別的所有商品
    - BY_SUPPLIER: 指定供應商的所有商品
    - BY_WAREHOUSE: 指定倉庫的商品
    """
    # 建立查詢
    statement = select(Product).where(
        Product.is_active == True,
        Product.is_deleted == False,
    )

    # 根據計算方式篩選
    if request.method == SuggestionMethod.BY_PRODUCT and request.product_id:
        statement = statement.where(Product.id == request.product_id)
    elif request.method == SuggestionMethod.BY_CATEGORY and request.category_id:
        statement = statement.where(Product.category_id == request.category_id)
    elif request.method == SuggestionMethod.BY_SUPPLIER and request.supplier_id:
        statement = statement.where(Product.supplier_id == request.supplier_id)

    result = await session.execute(statement)
    products = result.scalars().all()

    items: List[PurchaseSuggestionItem] = []
    supplier_ids: set = set()

    for product in products:
        # 取得庫存資訊
        current_stock = await _get_current_stock(
            session, product.id, request.warehouse_id
        )
        safety_stock = product.min_stock or 0

        # 對於 LOW_STOCK 方式，只處理低於安全庫存的商品
        if request.method == SuggestionMethod.LOW_STOCK:
            if current_stock >= safety_stock:
                continue

        # 計算在途庫存
        in_transit = 0
        if request.include_in_transit:
            in_transit = await _get_in_transit_quantity(session, product.id)

        # 預估銷售量
        forecast_sales = await _get_product_sales_forecast(
            session, product.id, request.forecast_days
        )

        # 取得供應商報價
        supplier_id, unit_price, min_order_quantity = await _get_supplier_price(
            session, product.id, request.supplier_id
        )

        # 計算建議採購數量
        suggested_quantity = await _calculate_suggested_quantity(
            safety_stock,
            forecast_sales,
            current_stock,
            in_transit,
            min_order_quantity,
        )

        # 如果不需要採購則跳過
        if suggested_quantity <= 0:
            continue

        # 取得供應商名稱
        supplier_name = None
        if supplier_id:
            stmt = select(Supplier.name).where(Supplier.id == supplier_id)
            result = await session.execute(stmt)
            supplier_name = result.scalar_one_or_none()
            supplier_ids.add(supplier_id)

        # 取得類別名稱
        category_name = None
        if product.category_id:
            stmt = select(Category.name).where(Category.id == product.category_id)
            result = await session.execute(stmt)
            category_name = result.scalar_one_or_none()

        shortage = safety_stock - current_stock

        items.append(
            PurchaseSuggestionItem(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                category_id=product.category_id,
                category_name=category_name,
                current_stock=current_stock,
                safety_stock=safety_stock,
                shortage=shortage if shortage > 0 else 0,
                in_transit=in_transit,
                forecast_sales=forecast_sales,
                suggested_quantity=suggested_quantity,
                unit_price=unit_price,
                suggested_amount=unit_price * suggested_quantity,
                min_order_quantity=min_order_quantity,
            )
        )

    # 計算摘要
    total_quantity = sum(item.suggested_quantity for item in items)
    total_amount = sum(item.suggested_amount for item in items)

    summary = PurchaseSuggestionSummary(
        total_items=len(items),
        total_quantity=total_quantity,
        total_amount=total_amount,
        suppliers_count=len(supplier_ids),
    )

    return PurchaseSuggestionResponse(
        generated_at=datetime.now(timezone.utc),
        method=request.method,
        forecast_days=request.forecast_days,
        items=items,
        summary=summary,
    )


@router.post(
    "/convert",
    response_model=ConvertToOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="轉採購單",
)
async def convert_to_orders(
    request: ConvertToOrderRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    將採購建議轉換為採購單

    可選擇依供應商分組，建立多張採購單
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="請選擇要採購的商品")

    # 驗證倉庫
    from app.kamesan.models.store import Warehouse
    stmt = select(Warehouse).where(Warehouse.id == request.warehouse_id)
    result = await session.execute(stmt)
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="倉庫不存在")

    # 依供應商分組
    supplier_items: Dict[int, List[ConvertToOrderRequest]] = defaultdict(list)
    for item in request.items:
        supplier_items[item.supplier_id].append(item)

    created_orders = []
    order_numbers = []
    total_amount = Decimal("0")

    numbering_service = NumberingService(session)

    for supplier_id, items in supplier_items.items():
        # 驗證供應商
        stmt = select(Supplier).where(Supplier.id == supplier_id)
        result = await session.execute(stmt)
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise HTTPException(
                status_code=404, detail=f"供應商 {supplier_id} 不存在"
            )

        # 產生採購單號
        order_number = await numbering_service.generate_number(
            DocumentType.PURCHASE_ORDER, commit=False
        )

        # 建立採購單
        purchase_order = PurchaseOrder(
            order_number=order_number,
            supplier_id=supplier_id,
            warehouse_id=request.warehouse_id,
            expected_date=request.expected_date,
            status=PurchaseOrderStatus.DRAFT,
            notes=request.notes,
            created_by=current_user.id,
        )
        session.add(purchase_order)
        await session.flush()

        # 建立採購單明細
        order_total = Decimal("0")
        for item in items:
            # 取得單價
            unit_price = item.unit_price
            if unit_price is None:
                _, unit_price, _ = await _get_supplier_price(
                    session, item.product_id, supplier_id
                )

            order_item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
            session.add(order_item)
            order_total += unit_price * item.quantity

        # 更新採購單總金額
        purchase_order.total_amount = order_total
        session.add(purchase_order)

        created_orders.append(purchase_order.id)
        order_numbers.append(order_number)
        total_amount += order_total

    await session.commit()

    return ConvertToOrderResponse(
        created_orders=created_orders,
        order_numbers=order_numbers,
        total_amount=total_amount,
        message=f"已建立 {len(created_orders)} 張採購單",
    )
