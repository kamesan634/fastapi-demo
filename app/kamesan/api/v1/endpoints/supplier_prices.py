"""
供應商價格管理 API 端點

提供供應商報價的 CRUD、價格比較、批量操作與補貨建議功能。

功能：
- F06-006: 供應商價格管理
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import and_, or_, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.inventory import Inventory
from app.kamesan.models.product import Product
from app.kamesan.models.purchase import SupplierPrice
from app.kamesan.models.store import Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.purchase import (
    ReplenishmentSuggestionResponse,
    SupplierPriceCreate,
    SupplierPriceResponse,
    SupplierPriceUpdate,
)
from app.kamesan.schemas.supplier_price import (
    ExpiringPriceResponse,
    ExpiringPricesListResponse,
    PriceAdjustmentPreview,
    PriceAdjustmentPreviewResponse,
    PriceAdjustmentRequest,
    PriceAdjustmentResult,
    PriceComparisonItem,
    PriceComparisonResponse,
    PriceHistoryEntry,
    PriceHistoryResponse,
    SupplierPriceBulkCreateRequest,
    SupplierPriceBulkCreateResult,
    SupplierPriceImportRequest,
    SupplierPriceImportResult,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SupplierPriceResponse], summary="取得供應商價格列表")
async def get_supplier_prices(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    supplier_id: Optional[int] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """取得供應商價格列表"""
    statement = select(SupplierPrice).where(SupplierPrice.is_deleted == False)

    if supplier_id is not None:
        statement = statement.where(SupplierPrice.supplier_id == supplier_id)
    if product_id is not None:
        statement = statement.where(SupplierPrice.product_id == product_id)
    if is_active is not None:
        statement = statement.where(SupplierPrice.is_active == is_active)

    count_result = await session.execute(statement)
    total = len(count_result.all())

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(SupplierPrice.id.desc())

    result = await session.execute(statement)
    prices = result.scalars().all()

    return PaginatedResponse.create(items=prices, total=total, page=page, page_size=page_size)


@router.get("/{price_id}", response_model=SupplierPriceResponse, summary="取得供應商價格詳情")
async def get_supplier_price(
    price_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得單一供應商價格詳情"""
    statement = select(SupplierPrice).where(
        SupplierPrice.id == price_id,
        SupplierPrice.is_deleted == False,
    )
    result = await session.execute(statement)
    price = result.scalar_one_or_none()

    if price is None:
        raise HTTPException(status_code=404, detail="找不到供應商價格")

    return price


@router.post("", response_model=SupplierPriceResponse, status_code=status.HTTP_201_CREATED, summary="建立供應商價格")
async def create_supplier_price(
    price_data: SupplierPriceCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的供應商報價"""
    # 檢查供應商是否存在
    supplier_result = await session.execute(
        select(Supplier).where(Supplier.id == price_data.supplier_id, Supplier.is_deleted == False)
    )
    if supplier_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="供應商不存在")

    # 檢查商品是否存在
    product_result = await session.execute(
        select(Product).where(Product.id == price_data.product_id, Product.is_deleted == False)
    )
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="商品不存在")

    price = SupplierPrice(**price_data.model_dump(exclude_unset=True))
    price.created_by = current_user.id

    session.add(price)
    await session.commit()
    await session.refresh(price)

    return price


@router.put("/{price_id}", response_model=SupplierPriceResponse, summary="更新供應商價格")
async def update_supplier_price(
    price_id: int,
    price_data: SupplierPriceUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新供應商報價"""
    statement = select(SupplierPrice).where(
        SupplierPrice.id == price_id,
        SupplierPrice.is_deleted == False,
    )
    result = await session.execute(statement)
    price = result.scalar_one_or_none()

    if price is None:
        raise HTTPException(status_code=404, detail="找不到供應商價格")

    update_data = price_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(price, field, value)

    price.updated_by = current_user.id

    await session.commit()
    await session.refresh(price)

    return price


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除供應商價格")
async def delete_supplier_price(
    price_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除供應商報價（軟刪除）"""
    statement = select(SupplierPrice).where(
        SupplierPrice.id == price_id,
        SupplierPrice.is_deleted == False,
    )
    result = await session.execute(statement)
    price = result.scalar_one_or_none()

    if price is None:
        raise HTTPException(status_code=404, detail="找不到供應商價格")

    price.is_deleted = True
    price.updated_by = current_user.id

    await session.commit()


@router.get("/by-product/{product_id}", response_model=list[SupplierPriceResponse], summary="取得商品的所有供應商價格")
async def get_prices_by_product(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得特定商品的所有供應商報價"""
    statement = (
        select(SupplierPrice)
        .where(
            SupplierPrice.product_id == product_id,
            SupplierPrice.is_active == True,
            SupplierPrice.is_deleted == False,
        )
        .order_by(SupplierPrice.unit_price)
    )

    result = await session.execute(statement)
    return result.scalars().all()


@router.get("/by-supplier/{supplier_id}", response_model=list[SupplierPriceResponse], summary="取得供應商的所有商品價格")
async def get_prices_by_supplier(
    supplier_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得特定供應商的所有商品報價"""
    statement = (
        select(SupplierPrice)
        .where(
            SupplierPrice.supplier_id == supplier_id,
            SupplierPrice.is_active == True,
            SupplierPrice.is_deleted == False,
        )
        .order_by(SupplierPrice.product_id)
    )

    result = await session.execute(statement)
    return result.scalars().all()


@router.get("/replenishment/suggestions", response_model=list[ReplenishmentSuggestionResponse], summary="取得補貨建議")
async def get_replenishment_suggestions(
    session: SessionDep,
    current_user: CurrentUser,
    warehouse_id: Optional[int] = Query(default=None, description="倉庫 ID"),
):
    """
    取得補貨建議

    查詢庫存低於最低庫存的商品，並建議最佳供應商。
    """
    # 查詢低庫存商品
    statement = (
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Product.is_deleted == False,
            Inventory.quantity < Product.min_stock,
        )
    )

    if warehouse_id is not None:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)

    result = await session.execute(statement)
    low_stock_items = result.all()

    suggestions = []
    for inventory, product, warehouse in low_stock_items:
        # 查詢最佳供應商（價格最低）
        price_statement = (
            select(SupplierPrice, Supplier)
            .join(Supplier, SupplierPrice.supplier_id == Supplier.id)
            .where(
                SupplierPrice.product_id == product.id,
                SupplierPrice.is_active == True,
                SupplierPrice.is_deleted == False,
                Supplier.is_deleted == False,
            )
            .order_by(SupplierPrice.unit_price)
            .limit(1)
        )

        price_result = await session.execute(price_statement)
        best_price = price_result.first()

        shortage = product.min_stock - inventory.quantity
        suggested_qty = product.max_stock - inventory.quantity if product.max_stock else shortage

        suggestion = ReplenishmentSuggestionResponse(
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            current_quantity=inventory.quantity,
            min_stock=product.min_stock,
            max_stock=product.max_stock or product.min_stock * 2,
            shortage_quantity=shortage,
            suggested_quantity=suggested_qty,
        )

        if best_price:
            supplier_price, supplier = best_price
            suggestion.suggested_supplier_id = supplier.id
            suggestion.suggested_supplier_name = supplier.name
            suggestion.unit_price = supplier_price.unit_price
            suggestion.lead_time_days = supplier_price.lead_time_days
            suggestion.estimated_cost = supplier_price.unit_price * suggested_qty

        suggestions.append(suggestion)

    return suggestions


# ==========================================
# 價格比較功能
# ==========================================
@router.get("/compare/{product_id}", response_model=PriceComparisonResponse, summary="比較商品供應商價格")
async def compare_product_prices(
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    include_inactive: bool = Query(default=False, description="是否包含停用的報價"),
):
    """
    比較指定商品的所有供應商報價

    列出所有供應商的價格並排序，方便選擇最佳供應商。
    """
    # 查詢商品
    product = await session.get(Product, product_id)
    if not product or product.is_deleted:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 查詢所有供應商報價
    statement = (
        select(SupplierPrice, Supplier)
        .join(Supplier, SupplierPrice.supplier_id == Supplier.id)
        .where(
            SupplierPrice.product_id == product_id,
            SupplierPrice.is_deleted == False,
            Supplier.is_deleted == False,
        )
    )

    if not include_inactive:
        today = date.today()
        statement = statement.where(
            SupplierPrice.is_active == True,
            SupplierPrice.effective_date <= today,
            or_(
                SupplierPrice.expiry_date == None,
                SupplierPrice.expiry_date >= today,
            ),
        )

    statement = statement.order_by(SupplierPrice.unit_price)

    result = await session.execute(statement)
    price_data = result.all()

    if not price_data:
        return PriceComparisonResponse(
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            supplier_count=0,
            comparison=[],
        )

    # 計算統計資料
    prices = [sp.unit_price for sp, _ in price_data]
    lowest_price = min(prices)
    highest_price = max(prices)
    average_price = sum(prices) / len(prices)

    # 建立比較列表
    comparison_items = []
    for rank, (supplier_price, supplier) in enumerate(price_data, 1):
        today = date.today()
        is_valid = (
            supplier_price.is_active
            and supplier_price.effective_date <= today
            and (supplier_price.expiry_date is None or supplier_price.expiry_date >= today)
        )

        price_diff_percent = None
        if lowest_price > 0:
            price_diff_percent = round(
                (supplier_price.unit_price - lowest_price) / lowest_price * 100, 2
            )

        comparison_items.append(
            PriceComparisonItem(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                unit_price=supplier_price.unit_price,
                min_order_quantity=supplier_price.min_order_quantity,
                lead_time_days=supplier_price.lead_time_days,
                is_valid=is_valid,
                price_rank=rank,
                price_diff_percent=price_diff_percent,
            )
        )

    return PriceComparisonResponse(
        product_id=product.id,
        product_code=product.code,
        product_name=product.name,
        lowest_price=lowest_price,
        highest_price=highest_price,
        average_price=round(average_price, 2),
        supplier_count=len(comparison_items),
        comparison=comparison_items,
    )


# ==========================================
# 批量操作功能
# ==========================================
@router.post("/bulk", response_model=SupplierPriceBulkCreateResult, summary="批量建立供應商價格")
async def bulk_create_supplier_prices(
    request: SupplierPriceBulkCreateRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    批量建立供應商價格

    一次新增多筆供應商報價，支援更新已存在的價格。
    """
    created_count = 0
    updated_count = 0
    error_count = 0
    errors: List[str] = []

    for idx, item in enumerate(request.items):
        try:
            # 驗證供應商
            supplier = await session.get(Supplier, item.supplier_id)
            if not supplier or supplier.is_deleted:
                errors.append(f"第 {idx + 1} 筆：供應商 ID {item.supplier_id} 不存在")
                error_count += 1
                continue

            # 驗證商品
            product = await session.get(Product, item.product_id)
            if not product or product.is_deleted:
                errors.append(f"第 {idx + 1} 筆：商品 ID {item.product_id} 不存在")
                error_count += 1
                continue

            # 檢查是否已存在
            existing_statement = select(SupplierPrice).where(
                SupplierPrice.supplier_id == item.supplier_id,
                SupplierPrice.product_id == item.product_id,
                SupplierPrice.is_deleted == False,
                SupplierPrice.is_active == True,
            )
            existing_result = await session.execute(existing_statement)
            existing_price = existing_result.scalar_one_or_none()

            if existing_price:
                if request.update_existing:
                    existing_price.unit_price = item.unit_price
                    existing_price.min_order_quantity = item.min_order_quantity
                    existing_price.lead_time_days = item.lead_time_days
                    if item.effective_date:
                        existing_price.effective_date = item.effective_date
                    if item.expiry_date:
                        existing_price.expiry_date = item.expiry_date
                    existing_price.updated_by = current_user.id
                    updated_count += 1
                else:
                    errors.append(
                        f"第 {idx + 1} 筆：供應商 {item.supplier_id} 商品 {item.product_id} 已有價格"
                    )
                    error_count += 1
            else:
                new_price = SupplierPrice(
                    supplier_id=item.supplier_id,
                    product_id=item.product_id,
                    unit_price=item.unit_price,
                    min_order_quantity=item.min_order_quantity,
                    lead_time_days=item.lead_time_days,
                    effective_date=item.effective_date or date.today(),
                    expiry_date=item.expiry_date,
                    created_by=current_user.id,
                )
                session.add(new_price)
                created_count += 1

        except Exception as e:
            errors.append(f"第 {idx + 1} 筆：處理錯誤 - {str(e)}")
            error_count += 1

    await session.commit()

    return SupplierPriceBulkCreateResult(
        created_count=created_count,
        updated_count=updated_count,
        error_count=error_count,
        errors=errors[:50],  # 最多回傳 50 筆錯誤
    )


@router.post("/import", response_model=SupplierPriceImportResult, summary="匯入供應商價格")
async def import_supplier_prices(
    request: SupplierPriceImportRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依代碼匯入供應商價格

    使用供應商代碼和商品代碼匯入價格資料。
    """
    success_count = 0
    error_count = 0
    errors: List[dict] = []

    # 預先載入供應商和商品對照表
    supplier_statement = select(Supplier).where(Supplier.is_deleted == False)
    supplier_result = await session.execute(supplier_statement)
    suppliers = {s.code: s for s in supplier_result.scalars().all()}

    product_statement = select(Product).where(Product.is_deleted == False)
    product_result = await session.execute(product_statement)
    products = {p.code: p for p in product_result.scalars().all()}

    for idx, row in enumerate(request.rows):
        try:
            # 查找供應商
            supplier = suppliers.get(row.supplier_code)
            if not supplier:
                errors.append({
                    "row": idx + 1,
                    "error": f"供應商代碼 {row.supplier_code} 不存在",
                })
                error_count += 1
                continue

            # 查找商品
            product = products.get(row.product_code)
            if not product:
                errors.append({
                    "row": idx + 1,
                    "error": f"商品代碼 {row.product_code} 不存在",
                })
                error_count += 1
                continue

            # 解析日期
            effective_date = date.today()
            expiry_date = None
            if row.effective_date:
                try:
                    effective_date = datetime.strptime(row.effective_date, "%Y-%m-%d").date()
                except ValueError:
                    errors.append({
                        "row": idx + 1,
                        "error": f"生效日期格式錯誤: {row.effective_date}",
                    })
                    error_count += 1
                    continue
            if row.expiry_date:
                try:
                    expiry_date = datetime.strptime(row.expiry_date, "%Y-%m-%d").date()
                except ValueError:
                    errors.append({
                        "row": idx + 1,
                        "error": f"失效日期格式錯誤: {row.expiry_date}",
                    })
                    error_count += 1
                    continue

            # 檢查是否已存在
            existing_statement = select(SupplierPrice).where(
                SupplierPrice.supplier_id == supplier.id,
                SupplierPrice.product_id == product.id,
                SupplierPrice.is_deleted == False,
                SupplierPrice.is_active == True,
            )
            existing_result = await session.execute(existing_statement)
            existing_price = existing_result.scalar_one_or_none()

            if existing_price:
                if request.update_existing:
                    existing_price.unit_price = row.unit_price
                    existing_price.min_order_quantity = row.min_order_quantity
                    existing_price.lead_time_days = row.lead_time_days
                    existing_price.effective_date = effective_date
                    existing_price.expiry_date = expiry_date
                    existing_price.updated_by = current_user.id
                    success_count += 1
                else:
                    errors.append({
                        "row": idx + 1,
                        "error": f"供應商 {row.supplier_code} 商品 {row.product_code} 已有價格",
                    })
                    error_count += 1
            else:
                new_price = SupplierPrice(
                    supplier_id=supplier.id,
                    product_id=product.id,
                    unit_price=row.unit_price,
                    min_order_quantity=row.min_order_quantity,
                    lead_time_days=row.lead_time_days,
                    effective_date=effective_date,
                    expiry_date=expiry_date,
                    created_by=current_user.id,
                )
                session.add(new_price)
                success_count += 1

        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
            error_count += 1

    await session.commit()

    return SupplierPriceImportResult(
        total_rows=len(request.rows),
        success_count=success_count,
        error_count=error_count,
        errors=errors[:100],
    )


@router.get("/export", summary="匯出供應商價格")
async def export_supplier_prices(
    session: SessionDep,
    current_user: CurrentUser,
    supplier_id: Optional[int] = Query(default=None, description="供應商 ID"),
    active_only: bool = Query(default=True, description="僅匯出啟用的價格"),
):
    """
    匯出供應商價格為 CSV

    可依供應商篩選，匯出價格資料。
    """
    import csv
    import io

    statement = (
        select(SupplierPrice, Supplier, Product)
        .join(Supplier, SupplierPrice.supplier_id == Supplier.id)
        .join(Product, SupplierPrice.product_id == Product.id)
        .where(
            SupplierPrice.is_deleted == False,
            Supplier.is_deleted == False,
            Product.is_deleted == False,
        )
    )

    if supplier_id:
        statement = statement.where(SupplierPrice.supplier_id == supplier_id)
    if active_only:
        statement = statement.where(SupplierPrice.is_active == True)

    statement = statement.order_by(Supplier.code, Product.code)

    result = await session.execute(statement)
    data = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "供應商代碼", "供應商名稱", "商品代碼", "商品名稱",
        "單價", "最小訂購量", "交貨天數", "生效日期", "失效日期", "狀態"
    ])

    for price, supplier, product in data:
        writer.writerow([
            supplier.code,
            supplier.name,
            product.code,
            product.name,
            str(price.unit_price),
            price.min_order_quantity,
            price.lead_time_days,
            price.effective_date.isoformat() if price.effective_date else "",
            price.expiry_date.isoformat() if price.expiry_date else "",
            "啟用" if price.is_active else "停用",
        ])

    output.seek(0)
    content = output.getvalue().encode("utf-8-sig")

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=supplier_prices.csv"},
    )


# ==========================================
# 價格到期提醒
# ==========================================
@router.get("/expiring", response_model=ExpiringPricesListResponse, summary="取得即將到期價格")
async def get_expiring_prices(
    session: SessionDep,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365, description="到期天數範圍"),
    supplier_id: Optional[int] = Query(default=None, description="供應商 ID"),
):
    """
    取得即將到期的供應商價格

    列出指定天數內即將到期的報價，方便提前更新。
    """
    today = date.today()
    end_date = date(today.year, today.month, today.day)
    from datetime import timedelta
    end_date = today + timedelta(days=days)

    statement = (
        select(SupplierPrice, Supplier, Product)
        .join(Supplier, SupplierPrice.supplier_id == Supplier.id)
        .join(Product, SupplierPrice.product_id == Product.id)
        .where(
            SupplierPrice.is_deleted == False,
            SupplierPrice.is_active == True,
            SupplierPrice.expiry_date != None,
            SupplierPrice.expiry_date >= today,
            SupplierPrice.expiry_date <= end_date,
            Supplier.is_deleted == False,
            Product.is_deleted == False,
        )
    )

    if supplier_id:
        statement = statement.where(SupplierPrice.supplier_id == supplier_id)

    statement = statement.order_by(SupplierPrice.expiry_date)

    result = await session.execute(statement)
    data = result.all()

    items = []
    for price, supplier, product in data:
        days_until_expiry = (price.expiry_date - today).days
        items.append(
            ExpiringPriceResponse(
                id=price.id,
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                unit_price=price.unit_price,
                expiry_date=price.expiry_date,
                days_until_expiry=days_until_expiry,
            )
        )

    return ExpiringPricesListResponse(
        items=items,
        total_count=len(items),
        expiring_within_days=days,
    )


# ==========================================
# 價格調整功能
# ==========================================
@router.post("/adjust/preview", response_model=PriceAdjustmentPreviewResponse, summary="預覽價格調整")
async def preview_price_adjustment(
    request: PriceAdjustmentRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    預覽價格調整結果

    在實際調整前預覽會影響的價格變化。
    """
    statement = (
        select(SupplierPrice, Product)
        .join(Product, SupplierPrice.product_id == Product.id)
        .where(
            SupplierPrice.supplier_id == request.supplier_id,
            SupplierPrice.is_deleted == False,
            SupplierPrice.is_active == True,
            Product.is_deleted == False,
        )
    )

    if request.product_ids:
        statement = statement.where(SupplierPrice.product_id.in_(request.product_ids))

    result = await session.execute(statement)
    data = result.all()

    previews = []
    for price, product in data:
        if request.adjustment_type == "percentage":
            adjustment = price.unit_price * request.adjustment_value / 100
        else:
            adjustment = request.adjustment_value

        new_price = max(Decimal("0"), price.unit_price + adjustment)

        previews.append(
            PriceAdjustmentPreview(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                current_price=price.unit_price,
                new_price=round(new_price, 2),
                difference=round(new_price - price.unit_price, 2),
            )
        )

    return PriceAdjustmentPreviewResponse(
        affected_count=len(previews),
        previews=previews,
    )


@router.post("/adjust", response_model=PriceAdjustmentResult, summary="執行價格調整")
async def apply_price_adjustment(
    request: PriceAdjustmentRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    執行供應商價格調整

    批量調整指定供應商的商品價格。
    """
    statement = select(SupplierPrice).where(
        SupplierPrice.supplier_id == request.supplier_id,
        SupplierPrice.is_deleted == False,
        SupplierPrice.is_active == True,
    )

    if request.product_ids:
        statement = statement.where(SupplierPrice.product_id.in_(request.product_ids))

    result = await session.execute(statement)
    prices = result.scalars().all()

    adjusted_count = 0
    new_effective_date = request.new_effective_date or date.today()

    for price in prices:
        if request.adjustment_type == "percentage":
            adjustment = price.unit_price * request.adjustment_value / 100
        else:
            adjustment = request.adjustment_value

        new_price = max(Decimal("0"), price.unit_price + adjustment)
        price.unit_price = round(new_price, 2)
        price.effective_date = new_effective_date
        price.updated_by = current_user.id
        adjusted_count += 1

    await session.commit()

    return PriceAdjustmentResult(
        adjusted_count=adjusted_count,
        new_effective_date=new_effective_date,
    )


# ==========================================
# 價格歷史
# ==========================================
@router.get("/history/{supplier_id}/{product_id}", response_model=PriceHistoryResponse, summary="取得價格歷史")
async def get_price_history(
    supplier_id: int,
    product_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得供應商商品價格歷史

    列出指定供應商對指定商品的所有報價記錄。
    """
    # 查詢供應商
    supplier = await session.get(Supplier, supplier_id)
    if not supplier or supplier.is_deleted:
        raise HTTPException(status_code=404, detail="供應商不存在")

    # 查詢商品
    product = await session.get(Product, product_id)
    if not product or product.is_deleted:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 查詢所有價格記錄（包含已刪除的）
    statement = (
        select(SupplierPrice)
        .where(
            SupplierPrice.supplier_id == supplier_id,
            SupplierPrice.product_id == product_id,
        )
        .order_by(SupplierPrice.effective_date.desc(), SupplierPrice.created_at.desc())
    )

    result = await session.execute(statement)
    prices = result.scalars().all()

    history = []
    current_price = None
    for price in prices:
        if price.is_active and not price.is_deleted:
            today = date.today()
            if price.effective_date <= today:
                if price.expiry_date is None or price.expiry_date >= today:
                    current_price = price.unit_price

        history.append(
            PriceHistoryEntry(
                id=price.id,
                unit_price=price.unit_price,
                min_order_quantity=price.min_order_quantity,
                lead_time_days=price.lead_time_days,
                effective_date=price.effective_date,
                expiry_date=price.expiry_date,
                is_active=price.is_active and not price.is_deleted,
                created_at=price.created_at,
                created_by=price.created_by,
            )
        )

    return PriceHistoryResponse(
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        product_id=product.id,
        product_code=product.code,
        product_name=product.name,
        current_price=current_price,
        history=history,
    )
