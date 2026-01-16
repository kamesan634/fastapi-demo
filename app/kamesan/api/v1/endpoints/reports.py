"""
報表 API 端點

提供儀表板摘要、銷售報表、庫存報表、採購報表及客戶報表功能。

端點：
- GET /reports/dashboard: 取得儀表板摘要
- GET /reports/sales: 取得銷售報表（依日期範圍）
- GET /reports/sales/trend: 取得銷售趨勢
- GET /reports/products/top: 取得熱銷商品排行
- GET /reports/inventory: 取得庫存報表
- GET /reports/purchases: 取得採購報表
- GET /reports/customers: 取得客戶報表
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, cast, Date
from sqlmodel import select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.customer import Customer, CustomerLevel
from app.kamesan.models.inventory import Inventory
from app.kamesan.models.order import Order, OrderItem, OrderStatus, SalesReturn, SalesReturnStatus
from app.kamesan.models.product import Category, Product
from app.kamesan.models.store import Store, Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.schemas.reports import (
    CategoryProfitResponse,
    ComparisonType,
    CostStructureResponse,
    CustomPeriodComparisonRequest,
    CustomerLevelDistributionResponse,
    CustomerReportResponse,
    DashboardSummaryResponse,
    ExportFormat,
    InventoryReportResponse,
    LowStockItemResponse,
    PeriodComparisonResponse,
    ProfitAnalysisResponse,
    PurchaseReportResponse,
    ReportExportRequest,
    ReportType,
    RevenueSummaryResponse,
    SalesComparisonItem,
    SalesComparisonResponse,
    SalesReportResponse,
    SalesTrendResponse,
    StoreProfitResponse,
    SupplierSummaryResponse,
    TopCustomerResponse,
    TopProductResponse,
)

router = APIRouter()


# ==========================================
# 輔助函數
# ==========================================
def get_today_start() -> datetime:
    """
    取得今日開始時間（UTC）

    回傳值：
        datetime: 今日 00:00:00 UTC
    """
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)


def get_yesterday_start() -> datetime:
    """
    取得昨日開始時間（UTC）

    回傳值：
        datetime: 昨日 00:00:00 UTC
    """
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    return datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.utc)


def calculate_growth_rate(today_value: Decimal, yesterday_value: Decimal) -> Decimal:
    """
    計算成長率

    參數：
        today_value: 今日數值
        yesterday_value: 昨日數值

    回傳值：
        Decimal: 成長率百分比（例如：0.15 表示 15% 成長）
    """
    if yesterday_value == 0:
        return Decimal("100.00") if today_value > 0 else Decimal("0.00")
    return ((today_value - yesterday_value) / yesterday_value * 100).quantize(
        Decimal("0.01")
    )


# ==========================================
# 儀表板 API
# ==========================================
@router.get(
    "/dashboard",
    response_model=DashboardSummaryResponse,
    summary="取得儀表板摘要",
)
async def get_dashboard_summary(
    session: SessionDep,
    current_user: CurrentUser,
) -> DashboardSummaryResponse:
    """
    取得儀表板摘要資訊

    提供今日營業概況，包含銷售額、訂單數、客戶數，以及與昨日的比較。
    同時顯示低庫存商品數量及待處理訂單數量。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        DashboardSummaryResponse: 儀表板摘要資訊

    權限要求：
        需要登入
    """
    today_start = get_today_start()
    yesterday_start = get_yesterday_start()
    today_end = today_start + timedelta(days=1)

    # 查詢今日銷售統計（已完成訂單）
    today_sales_statement = select(
        func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
        func.count(Order.id).label("order_count"),
        func.count(func.distinct(Order.customer_id)).label("customer_count"),
    ).where(
        Order.order_date >= today_start,
        Order.order_date < today_end,
        Order.status == OrderStatus.COMPLETED,
    )
    today_result = await session.execute(today_sales_statement)
    today_stats = today_result.one()

    today_sales = Decimal(str(today_stats.total_sales or 0))
    today_orders = today_stats.order_count or 0
    today_customers = today_stats.customer_count or 0

    # 計算今日平均訂單金額
    today_average_order_value = (
        (today_sales / today_orders).quantize(Decimal("0.01"))
        if today_orders > 0
        else Decimal("0.00")
    )

    # 查詢昨日銷售額（已完成訂單）
    yesterday_sales_statement = select(
        func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
    ).where(
        Order.order_date >= yesterday_start,
        Order.order_date < today_start,
        Order.status == OrderStatus.COMPLETED,
    )
    yesterday_result = await session.execute(yesterday_sales_statement)
    yesterday_stats = yesterday_result.one()
    yesterday_sales = Decimal(str(yesterday_stats.total_sales or 0))

    # 計算銷售成長率
    sales_growth_rate = calculate_growth_rate(today_sales, yesterday_sales)

    # 查詢低庫存商品數量
    low_stock_statement = (
        select(func.count(Inventory.id))
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.quantity <= Product.min_stock,
            Inventory.quantity > 0,
            Product.is_active == True,
        )
    )
    low_stock_result = await session.execute(low_stock_statement)
    low_stock_count = low_stock_result.scalar() or 0

    # 查詢待處理訂單數量
    pending_orders_statement = select(func.count(Order.id)).where(
        Order.status == OrderStatus.PENDING,
    )
    pending_orders_result = await session.execute(pending_orders_statement)
    pending_orders_count = pending_orders_result.scalar() or 0

    return DashboardSummaryResponse(
        today_sales=today_sales,
        today_orders=today_orders,
        today_customers=today_customers,
        low_stock_count=low_stock_count,
        yesterday_sales=yesterday_sales,
        sales_growth_rate=sales_growth_rate,
        today_average_order_value=today_average_order_value,
        pending_orders_count=pending_orders_count,
    )


# ==========================================
# 銷售報表 API
# ==========================================
@router.get(
    "/sales",
    response_model=List[SalesReportResponse],
    summary="取得銷售報表",
)
async def get_sales_report(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: date = Query(description="開始日期"),
    end_date: date = Query(description="結束日期"),
) -> List[SalesReportResponse]:
    """
    取得銷售報表（依日期範圍）

    依照指定的日期範圍，提供每日的銷售統計資料，
    包含銷售額、訂單數、平均訂單金額、退款金額、稅額及折扣金額。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        start_date: 開始日期
        end_date: 結束日期

    回傳值：
        List[SalesReportResponse]: 銷售報表列表（依日期分組）

    權限要求：
        需要登入
    """
    # 轉換為 datetime
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    # 查詢銷售統計（依日期分組）
    sales_statement = (
        select(
            cast(Order.order_date, Date).label("report_date"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.tax_amount), Decimal("0.00")).label("tax_amount"),
            func.coalesce(func.sum(Order.discount_amount), Decimal("0.00")).label("discount_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == OrderStatus.REFUNDED, Order.total_amount),
                        else_=Decimal("0.00"),
                    )
                ),
                Decimal("0.00"),
            ).label("refund_amount"),
        )
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status.in_([OrderStatus.COMPLETED, OrderStatus.REFUNDED]),
        )
        .group_by(cast(Order.order_date, Date))
        .order_by(cast(Order.order_date, Date))
    )

    result = await session.execute(sales_statement)
    rows = result.all()

    reports = []
    for row in rows:
        total_sales = Decimal(str(row.total_sales or 0))
        order_count = row.order_count or 0
        refund_amount = Decimal(str(row.refund_amount or 0))
        tax_amount = Decimal(str(row.tax_amount or 0))
        discount_amount = Decimal(str(row.discount_amount or 0))

        average_order_value = (
            (total_sales / order_count).quantize(Decimal("0.01"))
            if order_count > 0
            else Decimal("0.00")
        )
        net_sales = total_sales - refund_amount

        reports.append(
            SalesReportResponse(
                report_date=row.report_date,
                total_sales=total_sales,
                order_count=order_count,
                average_order_value=average_order_value,
                refund_amount=refund_amount,
                net_sales=net_sales,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
            )
        )

    return reports


@router.get(
    "/sales/trend",
    response_model=List[SalesTrendResponse],
    summary="取得銷售趨勢",
)
async def get_sales_trend(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: date = Query(description="開始日期"),
    end_date: date = Query(description="結束日期"),
) -> List[SalesTrendResponse]:
    """
    取得銷售趨勢資料

    依照指定的日期範圍，提供每日的銷售趨勢資料，
    用於繪製趨勢圖表。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        start_date: 開始日期
        end_date: 結束日期

    回傳值：
        List[SalesTrendResponse]: 銷售趨勢列表

    權限要求：
        需要登入
    """
    # 轉換為 datetime
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    # 查詢銷售趨勢（依日期分組）
    trend_statement = (
        select(
            cast(Order.order_date, Date).label("period_date"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("sales"),
            func.count(Order.id).label("order_count"),
        )
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(cast(Order.order_date, Date))
        .order_by(cast(Order.order_date, Date))
    )

    result = await session.execute(trend_statement)
    rows = result.all()

    trends = []
    for row in rows:
        trends.append(
            SalesTrendResponse(
                period=str(row.period_date),
                sales=Decimal(str(row.sales or 0)),
                order_count=row.order_count or 0,
            )
        )

    return trends


# ==========================================
# 商品報表 API
# ==========================================
@router.get(
    "/products/top",
    response_model=List[TopProductResponse],
    summary="取得熱銷商品排行",
)
async def get_top_products(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=100, description="取得筆數"),
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
) -> List[TopProductResponse]:
    """
    取得熱銷商品排行

    依照銷售收入排序，提供熱銷商品的排名及銷售統計資料。
    可依日期範圍篩選。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        limit: 取得筆數（預設 10）
        start_date: 開始日期（可選）
        end_date: 結束日期（可選）

    回傳值：
        List[TopProductResponse]: 熱銷商品排行列表

    權限要求：
        需要登入
    """
    # 建立查詢
    top_products_statement = (
        select(
            OrderItem.product_id,
            Product.code.label("sku"),
            Product.name.label("product_name"),
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.subtotal).label("revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Order.status == OrderStatus.COMPLETED)
    )

    # 日期篩選
    if start_date:
        start_datetime = datetime.combine(
            start_date, datetime.min.time(), tzinfo=timezone.utc
        )
        top_products_statement = top_products_statement.where(
            Order.order_date >= start_datetime
        )
    if end_date:
        end_datetime = datetime.combine(
            end_date, datetime.max.time(), tzinfo=timezone.utc
        )
        top_products_statement = top_products_statement.where(
            Order.order_date <= end_datetime
        )

    # 分組並排序
    top_products_statement = (
        top_products_statement.group_by(
            OrderItem.product_id,
            Product.code,
            Product.name,
            Category.name,
        )
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
    )

    result = await session.execute(top_products_statement)
    rows = result.all()

    products = []
    for rank, row in enumerate(rows, start=1):
        products.append(
            TopProductResponse(
                rank=rank,
                product_id=row.product_id,
                sku=row.sku or "",
                product_name=row.product_name or "",
                category_name=row.category_name or "未分類",
                quantity_sold=row.quantity_sold or 0,
                revenue=Decimal(str(row.revenue or 0)),
                order_count=row.order_count or 0,
            )
        )

    return products


# ==========================================
# 庫存報表 API
# ==========================================
@router.get(
    "/inventory",
    response_model=InventoryReportResponse,
    summary="取得庫存報表",
)
async def get_inventory_report(
    session: SessionDep,
    current_user: CurrentUser,
) -> InventoryReportResponse:
    """
    取得庫存報表

    提供庫存整體統計資料，包含商品總數、庫存總量、庫存價值，
    以及低庫存、缺貨、過剩庫存的商品數量。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        InventoryReportResponse: 庫存報表資訊

    權限要求：
        需要登入
    """
    # 查詢庫存統計
    inventory_stats_statement = (
        select(
            func.count(func.distinct(Inventory.product_id)).label("total_products"),
            func.coalesce(func.sum(Inventory.quantity), 0).label("total_quantity"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(Product.is_active == True)
    )
    stats_result = await session.execute(inventory_stats_statement)
    stats = stats_result.one()
    total_products = stats.total_products or 0
    total_quantity = stats.total_quantity or 0

    # 查詢庫存總價值（數量 * 成本價）
    stock_value_statement = (
        select(
            func.coalesce(
                func.sum(Inventory.quantity * Product.cost_price), Decimal("0.00")
            ).label("stock_value")
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(Product.is_active == True)
    )
    value_result = await session.execute(stock_value_statement)
    total_stock_value = Decimal(str(value_result.scalar() or 0))

    # 查詢低庫存商品數量（庫存量 <= 最低庫存量，但 > 0）
    low_stock_statement = (
        select(func.count(func.distinct(Inventory.product_id)))
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.quantity <= Product.min_stock,
            Inventory.quantity > 0,
            Product.is_active == True,
            Product.min_stock > 0,
        )
    )
    low_stock_result = await session.execute(low_stock_statement)
    low_stock_count = low_stock_result.scalar() or 0

    # 查詢缺貨商品數量（庫存量 = 0）
    out_of_stock_statement = (
        select(func.count(func.distinct(Inventory.product_id)))
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.quantity == 0,
            Product.is_active == True,
        )
    )
    out_of_stock_result = await session.execute(out_of_stock_statement)
    out_of_stock_count = out_of_stock_result.scalar() or 0

    # 查詢過剩庫存商品數量（庫存量 > 最高庫存量）
    over_stock_statement = (
        select(func.count(func.distinct(Inventory.product_id)))
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.quantity > Product.max_stock,
            Product.is_active == True,
            Product.max_stock > 0,
        )
    )
    over_stock_result = await session.execute(over_stock_statement)
    over_stock_count = over_stock_result.scalar() or 0

    # 查詢低庫存商品明細
    low_stock_items_statement = (
        select(
            Inventory.product_id,
            Product.code.label("sku"),
            Product.name.label("product_name"),
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity.label("current_quantity"),
            Product.min_stock.label("safety_stock"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Inventory.quantity <= Product.min_stock,
            Inventory.quantity > 0,
            Product.is_active == True,
            Product.min_stock > 0,
        )
        .order_by(Inventory.quantity)
        .limit(20)
    )
    low_stock_items_result = await session.execute(low_stock_items_statement)
    low_stock_items_rows = low_stock_items_result.all()

    low_stock_items = []
    for row in low_stock_items_rows:
        shortage = (row.safety_stock or 0) - (row.current_quantity or 0)
        low_stock_items.append(
            LowStockItemResponse(
                product_id=row.product_id,
                sku=row.sku or "",
                product_name=row.product_name or "",
                warehouse_name=row.warehouse_name or "",
                current_quantity=row.current_quantity or 0,
                safety_stock=row.safety_stock or 0,
                shortage_quantity=max(0, shortage),
            )
        )

    return InventoryReportResponse(
        total_products=total_products,
        total_quantity=total_quantity,
        total_stock_value=total_stock_value,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        over_stock_count=over_stock_count,
        low_stock_items=low_stock_items,
    )


# ==========================================
# 採購報表 API
# ==========================================
@router.get(
    "/purchases",
    response_model=PurchaseReportResponse,
    summary="取得採購報表",
)
async def get_purchase_report(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
) -> PurchaseReportResponse:
    """
    取得採購報表

    提供採購整體統計資料，包含訂單總數、總金額、已完成及待處理訂單數量，
    以及各供應商的採購摘要。

    注意：此功能需要 PurchaseOrder 模型。若尚未建立採購訂單模型，
    將以商品供應商為基礎，統計已入庫的商品數量作為採購參考。

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        start_date: 開始日期（可選）
        end_date: 結束日期（可選）

    回傳值：
        PurchaseReportResponse: 採購報表資訊

    權限要求：
        需要登入
    """
    # 由於目前沒有 PurchaseOrder 模型，我們使用供應商與商品的關係來產生摘要
    # 統計各供應商的商品成本價總和作為採購參考

    # 查詢供應商摘要
    supplier_statement = (
        select(
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            func.count(Product.id).label("product_count"),
            func.coalesce(
                func.sum(Product.cost_price), Decimal("0.00")
            ).label("total_cost"),
        )
        .outerjoin(Product, Supplier.id == Product.supplier_id)
        .where(Supplier.is_active == True)
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.sum(Product.cost_price).desc())
    )

    supplier_result = await session.execute(supplier_statement)
    supplier_rows = supplier_result.all()

    # 計算總金額
    total_amount = sum(Decimal(str(row.total_cost or 0)) for row in supplier_rows)

    # 建立供應商摘要列表
    supplier_summaries = []
    for row in supplier_rows:
        row_amount = Decimal(str(row.total_cost or 0))
        percentage = (
            (row_amount / total_amount * 100).quantize(Decimal("0.01"))
            if total_amount > 0
            else Decimal("0.00")
        )
        supplier_summaries.append(
            SupplierSummaryResponse(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name or "",
                order_count=row.product_count or 0,
                total_amount=row_amount,
                percentage=percentage,
            )
        )

    # 計算統計數據（由於沒有採購訂單，使用商品數據估算）
    total_orders = len(supplier_rows)
    completed_orders = total_orders  # 假設所有都已完成
    pending_orders = 0
    average_order_amount = (
        (total_amount / total_orders).quantize(Decimal("0.01"))
        if total_orders > 0
        else Decimal("0.00")
    )

    return PurchaseReportResponse(
        total_orders=total_orders,
        total_amount=total_amount,
        completed_orders=completed_orders,
        pending_orders=pending_orders,
        average_order_amount=average_order_amount,
        supplier_summaries=supplier_summaries,
    )


# ==========================================
# 客戶報表 API
# ==========================================
@router.get(
    "/customers",
    response_model=CustomerReportResponse,
    summary="取得客戶報表",
)
async def get_customer_report(
    session: SessionDep,
    current_user: CurrentUser,
) -> CustomerReportResponse:
    """
    取得客戶報表

    提供客戶整體統計資料，包含客戶總數、新增客戶、活躍客戶、休眠客戶，
    以及客戶等級分佈和頂級客戶排行。

    定義：
    - 活躍客戶：近 30 天內有消費的客戶
    - 休眠客戶：超過 90 天未消費的客戶
    - VIP 客戶：等級代碼為 'VIP' 或累計消費超過 50000 的客戶

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        CustomerReportResponse: 客戶報表資訊

    權限要求：
        需要登入
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 查詢客戶總數
    total_customers_statement = select(func.count(Customer.id)).where(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
    )
    total_customers_result = await session.execute(total_customers_statement)
    total_customers = total_customers_result.scalar() or 0

    # 查詢本月新增客戶數
    new_customers_statement = select(func.count(Customer.id)).where(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
        Customer.created_at >= month_start,
    )
    new_customers_result = await session.execute(new_customers_statement)
    new_customers_this_month = new_customers_result.scalar() or 0

    # 查詢活躍客戶數（近 30 天有訂單）
    active_customers_statement = (
        select(func.count(func.distinct(Order.customer_id)))
        .where(
            Order.order_date >= thirty_days_ago,
            Order.customer_id.isnot(None),
            Order.status == OrderStatus.COMPLETED,
        )
    )
    active_customers_result = await session.execute(active_customers_statement)
    active_customers = active_customers_result.scalar() or 0

    # 查詢休眠客戶數（超過 90 天未消費）
    # 先取得所有活躍客戶 ID
    recent_active_statement = (
        select(func.distinct(Order.customer_id))
        .where(
            Order.order_date >= ninety_days_ago,
            Order.customer_id.isnot(None),
            Order.status == OrderStatus.COMPLETED,
        )
    )
    recent_active_result = await session.execute(recent_active_statement)
    recent_active_ids = [row[0] for row in recent_active_result.all()]

    # 有訂單但超過 90 天未消費的客戶
    if recent_active_ids:
        dormant_statement = (
            select(func.count(func.distinct(Customer.id)))
            .where(
                Customer.is_active == True,
                Customer.deleted_at.is_(None),
                Customer.id.notin_(recent_active_ids),
                Customer.total_spending > 0,  # 曾經有消費過
            )
        )
    else:
        dormant_statement = (
            select(func.count(func.distinct(Customer.id)))
            .where(
                Customer.is_active == True,
                Customer.deleted_at.is_(None),
                Customer.total_spending > 0,  # 曾經有消費過
            )
        )
    dormant_customers_result = await session.execute(dormant_statement)
    dormant_customers = dormant_customers_result.scalar() or 0

    # 查詢平均客戶消費金額
    avg_spending_statement = select(
        func.coalesce(func.avg(Customer.total_spending), Decimal("0.00"))
    ).where(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
    )
    avg_spending_result = await session.execute(avg_spending_statement)
    average_customer_spending = Decimal(str(avg_spending_result.scalar() or 0)).quantize(
        Decimal("0.01")
    )

    # 查詢總點數餘額
    total_points_statement = select(
        func.coalesce(func.sum(Customer.points), 0)
    ).where(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
    )
    total_points_result = await session.execute(total_points_statement)
    total_points = total_points_result.scalar() or 0

    # 查詢 VIP 客戶數（等級代碼為 'VIP' 或累計消費超過 50000）
    vip_statement = (
        select(func.count(Customer.id))
        .outerjoin(CustomerLevel, Customer.level_id == CustomerLevel.id)
        .where(
            Customer.is_active == True,
            Customer.deleted_at.is_(None),
            (
                (CustomerLevel.code == "VIP")
                | (Customer.total_spending >= 50000)
            ),
        )
    )
    vip_result = await session.execute(vip_statement)
    vip_customers = vip_result.scalar() or 0

    # 查詢客戶等級分佈
    level_distribution_statement = (
        select(
            CustomerLevel.id.label("level_id"),
            CustomerLevel.name.label("level_name"),
            func.count(Customer.id).label("customer_count"),
        )
        .outerjoin(Customer, CustomerLevel.id == Customer.level_id)
        .where(
            CustomerLevel.is_active == True,
        )
        .group_by(CustomerLevel.id, CustomerLevel.name)
        .order_by(CustomerLevel.id)
    )
    level_distribution_result = await session.execute(level_distribution_statement)
    level_distribution_rows = level_distribution_result.all()

    level_distribution = []
    for row in level_distribution_rows:
        customer_count = row.customer_count or 0
        percentage = (
            (Decimal(customer_count) / Decimal(total_customers) * 100).quantize(
                Decimal("0.01")
            )
            if total_customers > 0
            else Decimal("0.00")
        )
        level_distribution.append(
            CustomerLevelDistributionResponse(
                level_id=row.level_id,
                level_name=row.level_name or "",
                customer_count=customer_count,
                percentage=percentage,
            )
        )

    # 查詢頂級客戶（依消費金額排序，取前 10 名）
    top_customers_statement = (
        select(
            Customer.id.label("customer_id"),
            Customer.code.label("member_no"),
            Customer.name.label("customer_name"),
            CustomerLevel.name.label("level_name"),
            Customer.total_spending.label("total_spent"),
            func.count(Order.id).label("total_orders"),
            func.max(Order.order_date).label("last_purchase_date"),
        )
        .outerjoin(CustomerLevel, Customer.level_id == CustomerLevel.id)
        .outerjoin(Order, Customer.id == Order.customer_id)
        .where(
            Customer.is_active == True,
            Customer.deleted_at.is_(None),
        )
        .group_by(
            Customer.id,
            Customer.code,
            Customer.name,
            CustomerLevel.name,
            Customer.total_spending,
        )
        .order_by(Customer.total_spending.desc())
        .limit(10)
    )
    top_customers_result = await session.execute(top_customers_statement)
    top_customers_rows = top_customers_result.all()

    top_customers = []
    for rank, row in enumerate(top_customers_rows, start=1):
        top_customers.append(
            TopCustomerResponse(
                rank=rank,
                customer_id=row.customer_id,
                member_no=row.member_no or "",
                customer_name=row.customer_name or "",
                level_name=row.level_name or "一般會員",
                total_spent=Decimal(str(row.total_spent or 0)),
                total_orders=row.total_orders or 0,
                last_purchase_date=row.last_purchase_date,
            )
        )

    return CustomerReportResponse(
        total_customers=total_customers,
        new_customers_this_month=new_customers_this_month,
        active_customers=active_customers,
        dormant_customers=dormant_customers,
        average_customer_spending=average_customer_spending,
        total_points=total_points,
        vip_customers=vip_customers,
        level_distribution=level_distribution,
        top_customers=top_customers,
    )


# ==========================================
# 利潤分析報表 API
# ==========================================
@router.get(
    "/profit/analysis",
    response_model=ProfitAnalysisResponse,
    summary="取得利潤分析報表",
)
async def get_profit_analysis(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: date = Query(description="開始日期"),
    end_date: date = Query(description="結束日期"),
) -> ProfitAnalysisResponse:
    """
    取得利潤分析報表

    提供指定期間的利潤分析資料，包含：
    - 營收摘要：銷售總額、退貨金額、折扣金額、淨營收
    - 成本結構：銷貨成本、毛利、毛利率
    - 各分類利潤分析
    - 各門市利潤分析
    - 同期比較

    參數：
        session: 資料庫 Session
        current_user: 當前登入使用者
        start_date: 開始日期
        end_date: 結束日期

    回傳值：
        ProfitAnalysisResponse: 利潤分析報表資訊
    """
    # 轉換為 datetime
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    # ========== 營收摘要 ==========
    # 查詢銷售總額（已完成訂單）
    sales_statement = select(
        func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
        func.coalesce(func.sum(Order.discount_amount), Decimal("0.00")).label("discount_amount"),
    ).where(
        Order.order_date >= start_datetime,
        Order.order_date <= end_datetime,
        Order.status == OrderStatus.COMPLETED,
    )
    sales_result = await session.execute(sales_statement)
    sales_stats = sales_result.one()
    total_sales = Decimal(str(sales_stats.total_sales or 0))
    discount_amount = Decimal(str(sales_stats.discount_amount or 0))

    # 查詢退貨金額
    return_statement = select(
        func.coalesce(func.sum(SalesReturn.total_amount), Decimal("0.00")).label("return_amount"),
    ).where(
        SalesReturn.return_date >= start_datetime,
        SalesReturn.return_date <= end_datetime,
        SalesReturn.status == SalesReturnStatus.COMPLETED,
    )
    return_result = await session.execute(return_statement)
    return_stats = return_result.one()
    return_amount = Decimal(str(return_stats.return_amount or 0))

    # 計算淨營收
    net_revenue = total_sales - return_amount - discount_amount

    revenue_summary = RevenueSummaryResponse(
        total_sales=total_sales,
        return_amount=return_amount,
        discount_amount=discount_amount,
        net_revenue=net_revenue,
        net_revenue_ratio=Decimal("100.00"),
    )

    # ========== 成本結構 ==========
    # 查詢銷貨成本（訂單明細的商品成本）
    cost_statement = (
        select(
            func.coalesce(
                func.sum(OrderItem.quantity * Product.cost_price), Decimal("0.00")
            ).label("cost_of_goods_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
    )
    cost_result = await session.execute(cost_statement)
    cost_stats = cost_result.one()
    cost_of_goods_sold = Decimal(str(cost_stats.cost_of_goods_sold or 0))

    # 計算毛利
    gross_profit = net_revenue - cost_of_goods_sold
    cost_ratio = (
        (cost_of_goods_sold / net_revenue * 100).quantize(Decimal("0.01"))
        if net_revenue > 0
        else Decimal("0.00")
    )
    gross_profit_margin = (
        (gross_profit / net_revenue * 100).quantize(Decimal("0.01"))
        if net_revenue > 0
        else Decimal("0.00")
    )

    cost_structure = CostStructureResponse(
        cost_of_goods_sold=cost_of_goods_sold,
        cost_ratio=cost_ratio,
        gross_profit=gross_profit,
        gross_profit_margin=gross_profit_margin,
    )

    # ========== 各分類利潤分析 ==========
    category_statement = (
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.coalesce(func.sum(OrderItem.subtotal), Decimal("0.00")).label("net_sales"),
            func.coalesce(
                func.sum(OrderItem.quantity * Product.cost_price), Decimal("0.00")
            ).label("cost"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.subtotal).desc())
    )
    category_result = await session.execute(category_statement)
    category_rows = category_result.all()

    total_profit = gross_profit if gross_profit > 0 else Decimal("1.00")
    category_profits = []
    for row in category_rows:
        cat_net_sales = Decimal(str(row.net_sales or 0))
        cat_cost = Decimal(str(row.cost or 0))
        cat_gross_profit = cat_net_sales - cat_cost
        cat_margin = (
            (cat_gross_profit / cat_net_sales * 100).quantize(Decimal("0.01"))
            if cat_net_sales > 0
            else Decimal("0.00")
        )
        cat_contribution = (
            (cat_gross_profit / total_profit * 100).quantize(Decimal("0.01"))
            if total_profit > 0
            else Decimal("0.00")
        )

        category_profits.append(
            CategoryProfitResponse(
                category_id=row.category_id,
                category_name=row.category_name or "未分類",
                net_sales=cat_net_sales,
                cost=cat_cost,
                gross_profit=cat_gross_profit,
                gross_profit_margin=cat_margin,
                profit_contribution=cat_contribution,
            )
        )

    # ========== 各門市利潤分析 ==========
    store_statement = (
        select(
            Store.id.label("store_id"),
            Store.name.label("store_name"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("net_sales"),
        )
        .outerjoin(Order, Store.id == Order.store_id)
        .where(
            Store.is_active == True,
        )
        .group_by(Store.id, Store.name)
        .order_by(func.sum(Order.total_amount).desc())
    )

    # 加上日期篩選
    store_statement = (
        select(
            Store.id.label("store_id"),
            Store.name.label("store_name"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("net_sales"),
        )
        .join(Order, Store.id == Order.store_id)
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(Store.id, Store.name)
        .order_by(func.sum(Order.total_amount).desc())
    )

    store_result = await session.execute(store_statement)
    store_rows = store_result.all()

    # 查詢各門市成本
    store_cost_statement = (
        select(
            Order.store_id,
            func.coalesce(
                func.sum(OrderItem.quantity * Product.cost_price), Decimal("0.00")
            ).label("cost"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(Order.store_id)
    )
    store_cost_result = await session.execute(store_cost_statement)
    store_costs = {row.store_id: Decimal(str(row.cost or 0)) for row in store_cost_result.all()}

    store_profits = []
    for row in store_rows:
        st_net_sales = Decimal(str(row.net_sales or 0))
        st_cost = store_costs.get(row.store_id, Decimal("0.00"))
        st_gross_profit = st_net_sales - st_cost
        st_margin = (
            (st_gross_profit / st_net_sales * 100).quantize(Decimal("0.01"))
            if st_net_sales > 0
            else Decimal("0.00")
        )

        store_profits.append(
            StoreProfitResponse(
                store_id=row.store_id,
                store_name=row.store_name or "未知門市",
                net_sales=st_net_sales,
                cost=st_cost,
                gross_profit=st_gross_profit,
                gross_profit_margin=st_margin,
            )
        )

    # ========== 同期比較 ==========
    # 計算上期時間範圍（相同天數的上一期）
    period_days = (end_date - start_date).days + 1
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=period_days - 1)
    prev_start_datetime = datetime.combine(prev_start_date, datetime.min.time(), tzinfo=timezone.utc)
    prev_end_datetime = datetime.combine(prev_end_date, datetime.max.time(), tzinfo=timezone.utc)

    # 查詢上期銷售統計
    prev_sales_statement = select(
        func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
        func.coalesce(func.sum(Order.discount_amount), Decimal("0.00")).label("discount_amount"),
    ).where(
        Order.order_date >= prev_start_datetime,
        Order.order_date <= prev_end_datetime,
        Order.status == OrderStatus.COMPLETED,
    )
    prev_sales_result = await session.execute(prev_sales_statement)
    prev_sales_stats = prev_sales_result.one()
    prev_total_sales = Decimal(str(prev_sales_stats.total_sales or 0))
    prev_discount_amount = Decimal(str(prev_sales_stats.discount_amount or 0))

    # 查詢上期退貨
    prev_return_statement = select(
        func.coalesce(func.sum(SalesReturn.total_amount), Decimal("0.00")).label("return_amount"),
    ).where(
        SalesReturn.return_date >= prev_start_datetime,
        SalesReturn.return_date <= prev_end_datetime,
        SalesReturn.status == SalesReturnStatus.COMPLETED,
    )
    prev_return_result = await session.execute(prev_return_statement)
    prev_return_stats = prev_return_result.one()
    prev_return_amount = Decimal(str(prev_return_stats.return_amount or 0))
    prev_net_revenue = prev_total_sales - prev_return_amount - prev_discount_amount

    # 查詢上期成本
    prev_cost_statement = (
        select(
            func.coalesce(
                func.sum(OrderItem.quantity * Product.cost_price), Decimal("0.00")
            ).label("cost_of_goods_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Order.order_date >= prev_start_datetime,
            Order.order_date <= prev_end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
    )
    prev_cost_result = await session.execute(prev_cost_statement)
    prev_cost_stats = prev_cost_result.one()
    prev_cost_of_goods_sold = Decimal(str(prev_cost_stats.cost_of_goods_sold or 0))
    prev_gross_profit = prev_net_revenue - prev_cost_of_goods_sold
    prev_gross_profit_margin = (
        (prev_gross_profit / prev_net_revenue * 100).quantize(Decimal("0.01"))
        if prev_net_revenue > 0
        else Decimal("0.00")
    )

    # 建立同期比較
    period_comparison = [
        PeriodComparisonResponse(
            metric="淨銷售額",
            current_value=net_revenue,
            previous_value=prev_net_revenue,
            change=net_revenue - prev_net_revenue,
            change_rate=calculate_growth_rate(net_revenue, prev_net_revenue),
        ),
        PeriodComparisonResponse(
            metric="銷貨成本",
            current_value=cost_of_goods_sold,
            previous_value=prev_cost_of_goods_sold,
            change=cost_of_goods_sold - prev_cost_of_goods_sold,
            change_rate=calculate_growth_rate(cost_of_goods_sold, prev_cost_of_goods_sold),
        ),
        PeriodComparisonResponse(
            metric="毛利",
            current_value=gross_profit,
            previous_value=prev_gross_profit,
            change=gross_profit - prev_gross_profit,
            change_rate=calculate_growth_rate(gross_profit, prev_gross_profit),
        ),
        PeriodComparisonResponse(
            metric="毛利率",
            current_value=gross_profit_margin,
            previous_value=prev_gross_profit_margin,
            change=gross_profit_margin - prev_gross_profit_margin,
            change_rate=None,
        ),
    ]

    return ProfitAnalysisResponse(
        period_start=start_date,
        period_end=end_date,
        revenue_summary=revenue_summary,
        cost_structure=cost_structure,
        category_profits=category_profits,
        store_profits=store_profits,
        period_comparison=period_comparison,
    )


# ==========================================
# 報表匯出 API
# ==========================================
@router.post(
    "/export",
    summary="匯出報表",
    response_class=StreamingResponse,
)
async def export_report(
    export_request: ReportExportRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    匯出報表

    支援格式：CSV、Excel（需安裝 openpyxl）、PDF（需安裝 reportlab）

    參數：
        export_request: 匯出請求
        session: 資料庫 Session
        current_user: 當前登入使用者

    回傳值：
        StreamingResponse: 檔案下載回應
    """
    report_type = export_request.report_type
    export_format = export_request.format
    start_date = export_request.start_date
    end_date = export_request.end_date

    # 設定預設日期範圍（近 30 天）
    if not end_date:
        end_date = datetime.now(timezone.utc).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # 轉換為 datetime
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    # 根據報表類型取得資料
    if report_type == ReportType.SALES_DAILY:
        data, headers, filename = await _get_sales_daily_data(
            session, start_datetime, end_datetime
        )
    elif report_type == ReportType.TOP_PRODUCTS:
        data, headers, filename = await _get_top_products_data(
            session, start_datetime, end_datetime
        )
    elif report_type == ReportType.INVENTORY:
        data, headers, filename = await _get_inventory_data(session)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的報表類型: {report_type}",
        )

    # 匯出為指定格式
    if export_format == ExportFormat.CSV:
        return _export_csv(data, headers, filename, export_request)
    elif export_format == ExportFormat.EXCEL:
        raise HTTPException(
            status_code=501,
            detail="Excel 匯出功能需要安裝 openpyxl 套件",
        )
    elif export_format == ExportFormat.PDF:
        raise HTTPException(
            status_code=501,
            detail="PDF 匯出功能需要安裝 reportlab 套件",
        )

    raise HTTPException(status_code=400, detail=f"不支援的匯出格式: {export_format}")


async def _get_sales_daily_data(
    session: SessionDep,
    start_datetime: datetime,
    end_datetime: datetime,
) -> tuple[List[dict], List[str], str]:
    """取得銷售日報資料"""
    statement = (
        select(
            cast(Order.order_date, Date).label("report_date"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("total_sales"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.tax_amount), Decimal("0.00")).label("tax_amount"),
            func.coalesce(func.sum(Order.discount_amount), Decimal("0.00")).label("discount_amount"),
        )
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(cast(Order.order_date, Date))
        .order_by(cast(Order.order_date, Date))
    )

    result = await session.execute(statement)
    rows = result.all()

    headers = ["日期", "銷售總額", "訂單數", "稅額", "折扣金額", "淨銷售額"]
    data = []
    for row in rows:
        total_sales = Decimal(str(row.total_sales or 0))
        discount_amount = Decimal(str(row.discount_amount or 0))
        net_sales = total_sales - discount_amount
        data.append({
            "日期": str(row.report_date),
            "銷售總額": str(total_sales),
            "訂單數": row.order_count or 0,
            "稅額": str(row.tax_amount or 0),
            "折扣金額": str(discount_amount),
            "淨銷售額": str(net_sales),
        })

    return data, headers, "sales_daily_report"


async def _get_top_products_data(
    session: SessionDep,
    start_datetime: datetime,
    end_datetime: datetime,
    limit: int = 50,
) -> tuple[List[dict], List[str], str]:
    """取得熱銷商品資料"""
    statement = (
        select(
            Product.code.label("sku"),
            Product.name.label("product_name"),
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.subtotal).label("revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
        .group_by(Product.code, Product.name, Category.name)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
    )

    result = await session.execute(statement)
    rows = result.all()

    headers = ["排名", "商品編號", "商品名稱", "分類", "銷售數量", "銷售金額", "訂單數"]
    data = []
    for rank, row in enumerate(rows, start=1):
        data.append({
            "排名": rank,
            "商品編號": row.sku or "",
            "商品名稱": row.product_name or "",
            "分類": row.category_name or "未分類",
            "銷售數量": row.quantity_sold or 0,
            "銷售金額": str(row.revenue or 0),
            "訂單數": row.order_count or 0,
        })

    return data, headers, "top_products_report"


async def _get_inventory_data(
    session: SessionDep,
) -> tuple[List[dict], List[str], str]:
    """取得庫存資料"""
    statement = (
        select(
            Product.code.label("sku"),
            Product.name.label("product_name"),
            Category.name.label("category_name"),
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity.label("quantity"),
            Product.min_stock,
            Product.max_stock,
            Product.cost_price,
        )
        .join(Product, Inventory.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(Product.is_active == True)
        .order_by(Product.code)
    )

    result = await session.execute(statement)
    rows = result.all()

    headers = ["商品編號", "商品名稱", "分類", "倉庫", "庫存數量", "安全庫存", "最高庫存", "庫存價值"]
    data = []
    for row in rows:
        quantity = row.quantity or 0
        cost_price = Decimal(str(row.cost_price or 0))
        stock_value = quantity * cost_price
        data.append({
            "商品編號": row.sku or "",
            "商品名稱": row.product_name or "",
            "分類": row.category_name or "未分類",
            "倉庫": row.warehouse_name or "",
            "庫存數量": quantity,
            "安全庫存": row.min_stock or 0,
            "最高庫存": row.max_stock or 0,
            "庫存價值": str(stock_value),
        })

    return data, headers, "inventory_report"


def _export_csv(
    data: List[dict],
    headers: List[str],
    filename: str,
    export_request: ReportExportRequest,
) -> StreamingResponse:
    """匯出 CSV 格式"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)

    # 寫入標題
    if export_request.include_header:
        writer.writeheader()

    # 寫入資料
    for row in data:
        writer.writerow(row)

    # 寫入合計（如果適用）
    if export_request.include_summary and data:
        # 嘗試計算數值欄位的合計
        summary_row = {}
        for header in headers:
            if header in ["銷售總額", "稅額", "折扣金額", "淨銷售額", "銷售金額", "庫存價值"]:
                try:
                    total = sum(Decimal(str(row.get(header, 0))) for row in data)
                    summary_row[header] = str(total)
                except:
                    summary_row[header] = ""
            elif header in ["訂單數", "銷售數量", "庫存數量"]:
                try:
                    total = sum(int(row.get(header, 0)) for row in data)
                    summary_row[header] = str(total)
                except:
                    summary_row[header] = ""
            elif header == "日期" or header == "排名":
                summary_row[header] = "合計"
            else:
                summary_row[header] = ""

        writer.writerow(summary_row)

    output.seek(0)

    # 設定檔案名稱
    export_filename = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename={export_filename}",
        },
    )


# ==========================================
# 期間比較端點
# ==========================================
async def _get_period_sales_summary(
    session: SessionDep,
    start_date: date,
    end_date: date,
) -> dict:
    """取得期間銷售摘要"""
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    # 銷售統計
    statement = (
        select(
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_sales"),
            func.avg(Order.total_amount).label("avg_order_value"),
        )
        .where(
            Order.order_date >= start_datetime,
            Order.order_date <= end_datetime,
            Order.status == OrderStatus.COMPLETED,
        )
    )
    result = await session.execute(statement)
    row = result.one()

    # 退款統計
    refund_statement = (
        select(func.sum(SalesReturn.refund_amount))
        .where(
            SalesReturn.return_date >= start_datetime,
            SalesReturn.return_date <= end_datetime,
            SalesReturn.status == SalesReturnStatus.COMPLETED,
        )
    )
    refund_result = await session.execute(refund_statement)
    refund_amount = refund_result.scalar() or Decimal("0")

    total_sales = Decimal(str(row.total_sales or 0))
    order_count = row.order_count or 0
    avg_order_value = Decimal(str(row.avg_order_value or 0))
    net_sales = total_sales - refund_amount

    return {
        "total_sales": total_sales,
        "order_count": order_count,
        "avg_order_value": avg_order_value,
        "refund_amount": refund_amount,
        "net_sales": net_sales,
    }


def _calculate_comparison_items(
    current: dict,
    previous: dict,
) -> List[SalesComparisonItem]:
    """計算比較項目"""
    items = []

    metrics = [
        ("總銷售額", "total_sales"),
        ("訂單數", "order_count"),
        ("平均訂單金額", "avg_order_value"),
        ("退款金額", "refund_amount"),
        ("淨銷售額", "net_sales"),
    ]

    for label, key in metrics:
        current_value = Decimal(str(current.get(key, 0)))
        previous_value = Decimal(str(previous.get(key, 0)))
        change_amount = current_value - previous_value

        change_rate = None
        if previous_value != 0:
            change_rate = (change_amount / previous_value * 100).quantize(Decimal("0.01"))

        items.append(SalesComparisonItem(
            metric=label,
            current_value=current_value,
            previous_value=previous_value,
            change_amount=change_amount,
            change_rate=change_rate,
        ))

    return items


@router.get(
    "/comparison/yoy",
    response_model=SalesComparisonResponse,
    summary="年對年銷售比較",
)
async def get_yoy_comparison(
    session: SessionDep,
    current_user: CurrentUser,
    year: Optional[int] = Query(default=None, description="年份（預設為今年）"),
    month: Optional[int] = Query(default=None, ge=1, le=12, description="月份（可選）"),
):
    """
    年對年 (Year-over-Year) 銷售比較

    比較指定年份與前一年同期的銷售數據。
    """
    today = datetime.now(timezone.utc).date()
    current_year = year or today.year

    if month:
        # 比較特定月份
        current_start = date(current_year, month, 1)
        if month == 12:
            current_end = date(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            current_end = date(current_year, month + 1, 1) - timedelta(days=1)

        previous_start = date(current_year - 1, month, 1)
        if month == 12:
            previous_end = date(current_year, 1, 1) - timedelta(days=1)
        else:
            previous_end = date(current_year - 1, month + 1, 1) - timedelta(days=1)

        current_period = f"{current_year}年{month}月"
        previous_period = f"{current_year - 1}年{month}月"
    else:
        # 比較整年
        current_start = date(current_year, 1, 1)
        current_end = date(current_year, 12, 31)
        previous_start = date(current_year - 1, 1, 1)
        previous_end = date(current_year - 1, 12, 31)

        current_period = f"{current_year}年"
        previous_period = f"{current_year - 1}年"

    current_data = await _get_period_sales_summary(session, current_start, current_end)
    previous_data = await _get_period_sales_summary(session, previous_start, previous_end)

    items = _calculate_comparison_items(current_data, previous_data)

    return SalesComparisonResponse(
        comparison_type="yoy",
        current_period=current_period,
        previous_period=previous_period,
        items=items,
    )


@router.get(
    "/comparison/mom",
    response_model=SalesComparisonResponse,
    summary="月對月銷售比較",
)
async def get_mom_comparison(
    session: SessionDep,
    current_user: CurrentUser,
    year: Optional[int] = Query(default=None, description="年份"),
    month: Optional[int] = Query(default=None, ge=1, le=12, description="月份"),
):
    """
    月對月 (Month-over-Month) 銷售比較

    比較指定月份與前一個月的銷售數據。
    """
    today = datetime.now(timezone.utc).date()
    current_year = year or today.year
    current_month = month or today.month

    # 本期
    current_start = date(current_year, current_month, 1)
    if current_month == 12:
        current_end = date(current_year + 1, 1, 1) - timedelta(days=1)
    else:
        current_end = date(current_year, current_month + 1, 1) - timedelta(days=1)

    # 前期
    if current_month == 1:
        previous_year = current_year - 1
        previous_month = 12
    else:
        previous_year = current_year
        previous_month = current_month - 1

    previous_start = date(previous_year, previous_month, 1)
    if previous_month == 12:
        previous_end = date(previous_year + 1, 1, 1) - timedelta(days=1)
    else:
        previous_end = date(previous_year, previous_month + 1, 1) - timedelta(days=1)

    current_data = await _get_period_sales_summary(session, current_start, current_end)
    previous_data = await _get_period_sales_summary(session, previous_start, previous_end)

    items = _calculate_comparison_items(current_data, previous_data)

    return SalesComparisonResponse(
        comparison_type="mom",
        current_period=f"{current_year}年{current_month}月",
        previous_period=f"{previous_year}年{previous_month}月",
        items=items,
    )


@router.get(
    "/comparison/wow",
    response_model=SalesComparisonResponse,
    summary="週對週銷售比較",
)
async def get_wow_comparison(
    session: SessionDep,
    current_user: CurrentUser,
    weeks_ago: int = Query(default=0, ge=0, description="幾週前（0=本週）"),
):
    """
    週對週 (Week-over-Week) 銷售比較

    比較指定週與前一週的銷售數據。
    """
    today = datetime.now(timezone.utc).date()

    # 計算本週開始（週一）
    current_week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_ago)
    current_week_end = current_week_start + timedelta(days=6)

    # 計算上週
    previous_week_start = current_week_start - timedelta(weeks=1)
    previous_week_end = previous_week_start + timedelta(days=6)

    current_data = await _get_period_sales_summary(session, current_week_start, current_week_end)
    previous_data = await _get_period_sales_summary(session, previous_week_start, previous_week_end)

    items = _calculate_comparison_items(current_data, previous_data)

    return SalesComparisonResponse(
        comparison_type="wow",
        current_period=f"{current_week_start} ~ {current_week_end}",
        previous_period=f"{previous_week_start} ~ {previous_week_end}",
        items=items,
    )


@router.post(
    "/comparison/custom",
    response_model=SalesComparisonResponse,
    summary="自訂期間銷售比較",
)
async def get_custom_comparison(
    request: CustomPeriodComparisonRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    自訂期間銷售比較

    比較兩個自訂期間的銷售數據。
    """
    current_data = await _get_period_sales_summary(
        session, request.period1_start, request.period1_end
    )
    previous_data = await _get_period_sales_summary(
        session, request.period2_start, request.period2_end
    )

    items = _calculate_comparison_items(current_data, previous_data)

    return SalesComparisonResponse(
        comparison_type="custom",
        current_period=f"{request.period1_start} ~ {request.period1_end}",
        previous_period=f"{request.period2_start} ~ {request.period2_end}",
        items=items,
    )
