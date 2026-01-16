"""
報表相關 Schema 模型

定義儀表板、銷售報表、庫存報表、採購報表、客戶報表的回應模型。

模型：
- DashboardSummaryResponse: 儀表板摘要回應
- SalesReportResponse: 銷售報表回應
- TopProductResponse: 熱銷商品回應
- LowStockItemResponse: 低庫存商品回應
- InventoryReportResponse: 庫存報表回應
- SupplierSummaryResponse: 供應商摘要回應
- PurchaseReportResponse: 採購報表回應
- CustomerLevelDistributionResponse: 客戶等級分佈回應
- TopCustomerResponse: 頂級客戶回應
- CustomerReportResponse: 客戶報表回應
- SalesTrendResponse: 銷售趨勢回應
"""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """報表類型"""

    SALES_DAILY = "sales_daily"  # 銷售日報
    SALES_SUMMARY = "sales_summary"  # 銷售彙總
    INVENTORY = "inventory"  # 庫存報表
    PROFIT_ANALYSIS = "profit_analysis"  # 利潤分析
    CUSTOMER = "customer"  # 客戶報表
    TOP_PRODUCTS = "top_products"  # 熱銷商品


class ExportFormat(str, Enum):
    """匯出格式"""

    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


# ==========================================
# 儀表板模型
# ==========================================
class DashboardSummaryResponse(BaseModel):
    """
    儀表板摘要回應模型

    提供今日營業概況、與昨日比較及待處理事項的摘要資訊。

    屬性：
    - today_sales: 今日銷售額
    - today_orders: 今日訂單數
    - today_customers: 今日客戶數
    - low_stock_count: 低庫存商品數量
    - yesterday_sales: 昨日銷售額
    - sales_growth_rate: 銷售成長率（與昨日相比）
    - today_average_order_value: 今日平均訂單金額
    - pending_orders_count: 待處理訂單數量
    """

    today_sales: Decimal = Field(description="今日銷售額")
    today_orders: int = Field(description="今日訂單數")
    today_customers: int = Field(description="今日客戶數")
    low_stock_count: int = Field(description="低庫存商品數量")
    yesterday_sales: Decimal = Field(description="昨日銷售額")
    sales_growth_rate: Decimal = Field(description="銷售成長率（與昨日相比）")
    today_average_order_value: Decimal = Field(description="今日平均訂單金額")
    pending_orders_count: int = Field(description="待處理訂單數量")

    model_config = {"from_attributes": True}


# ==========================================
# 銷售報表模型
# ==========================================
class SalesReportResponse(BaseModel):
    """
    銷售報表回應模型

    提供特定日期的銷售統計資料，包含銷售額、訂單數、退款及稅額等資訊。

    屬性：
    - date: 報表日期
    - total_sales: 總銷售額
    - order_count: 訂單數量
    - average_order_value: 平均訂單金額
    - refund_amount: 退款金額
    - net_sales: 淨銷售額（總銷售額減退款）
    - tax_amount: 稅額
    - discount_amount: 折扣金額
    """

    report_date: date_type = Field(description="報表日期")
    total_sales: Decimal = Field(description="總銷售額")
    order_count: int = Field(description="訂單數量")
    average_order_value: Decimal = Field(description="平均訂單金額")
    refund_amount: Decimal = Field(description="退款金額")
    net_sales: Decimal = Field(description="淨銷售額（總銷售額減退款）")
    tax_amount: Decimal = Field(description="稅額")
    discount_amount: Decimal = Field(description="折扣金額")

    model_config = {"from_attributes": True}


class TopProductResponse(BaseModel):
    """
    熱銷商品回應模型

    提供熱銷商品的排名及銷售統計資料。

    屬性：
    - rank: 排名
    - product_id: 商品 ID
    - sku: 商品貨號
    - product_name: 商品名稱
    - category_name: 分類名稱
    - quantity_sold: 銷售數量
    - revenue: 銷售收入
    - order_count: 訂單數量
    """

    rank: int = Field(description="排名")
    product_id: int = Field(description="商品 ID")
    sku: str = Field(description="商品貨號")
    product_name: str = Field(description="商品名稱")
    category_name: str = Field(description="分類名稱")
    quantity_sold: int = Field(description="銷售數量")
    revenue: Decimal = Field(description="銷售收入")
    order_count: int = Field(description="訂單數量")

    model_config = {"from_attributes": True}


class SalesTrendResponse(BaseModel):
    """
    銷售趨勢回應模型

    提供特定期間的銷售趨勢資料，用於繪製趨勢圖表。

    屬性：
    - period: 期間標籤（如：2024-01、2024-W01、2024-01-01）
    - sales: 銷售額
    - order_count: 訂單數量
    """

    period: str = Field(description="期間標籤（如：2024-01、2024-W01、2024-01-01）")
    sales: Decimal = Field(description="銷售額")
    order_count: int = Field(description="訂單數量")

    model_config = {"from_attributes": True}


# ==========================================
# 庫存報表模型
# ==========================================
class LowStockItemResponse(BaseModel):
    """
    低庫存商品回應模型

    提供低庫存商品的詳細資訊，包含目前數量、安全庫存及短缺數量。

    屬性：
    - product_id: 商品 ID
    - sku: 商品貨號
    - product_name: 商品名稱
    - warehouse_name: 倉庫名稱
    - current_quantity: 目前庫存數量
    - safety_stock: 安全庫存量
    - shortage_quantity: 短缺數量
    """

    product_id: int = Field(description="商品 ID")
    sku: str = Field(description="商品貨號")
    product_name: str = Field(description="商品名稱")
    warehouse_name: str = Field(description="倉庫名稱")
    current_quantity: int = Field(description="目前庫存數量")
    safety_stock: int = Field(description="安全庫存量")
    shortage_quantity: int = Field(description="短缺數量")

    model_config = {"from_attributes": True}


class InventoryReportResponse(BaseModel):
    """
    庫存報表回應模型

    提供庫存整體統計資料，包含商品總數、庫存價值及各類庫存狀態數量。

    屬性：
    - total_products: 商品總數
    - total_quantity: 總庫存數量
    - total_stock_value: 庫存總價值
    - low_stock_count: 低庫存商品數量
    - out_of_stock_count: 缺貨商品數量
    - over_stock_count: 過剩庫存商品數量
    - low_stock_items: 低庫存商品列表
    """

    total_products: int = Field(description="商品總數")
    total_quantity: int = Field(description="總庫存數量")
    total_stock_value: Decimal = Field(description="庫存總價值")
    low_stock_count: int = Field(description="低庫存商品數量")
    out_of_stock_count: int = Field(description="缺貨商品數量")
    over_stock_count: int = Field(description="過剩庫存商品數量")
    low_stock_items: List[LowStockItemResponse] = Field(
        default=[], description="低庫存商品列表"
    )

    model_config = {"from_attributes": True}


# ==========================================
# 採購報表模型
# ==========================================
class SupplierSummaryResponse(BaseModel):
    """
    供應商摘要回應模型

    提供供應商的採購統計資料，包含訂單數量、金額及佔比。

    屬性：
    - supplier_id: 供應商 ID
    - supplier_name: 供應商名稱
    - order_count: 採購訂單數量
    - total_amount: 採購總金額
    - percentage: 佔總採購金額百分比
    """

    supplier_id: int = Field(description="供應商 ID")
    supplier_name: str = Field(description="供應商名稱")
    order_count: int = Field(description="採購訂單數量")
    total_amount: Decimal = Field(description="採購總金額")
    percentage: Decimal = Field(description="佔總採購金額百分比")

    model_config = {"from_attributes": True}


class PurchaseReportResponse(BaseModel):
    """
    採購報表回應模型

    提供採購整體統計資料，包含訂單數量、金額及供應商摘要。

    屬性：
    - total_orders: 採購訂單總數
    - total_amount: 採購總金額
    - completed_orders: 已完成訂單數
    - pending_orders: 待處理訂單數
    - average_order_amount: 平均訂單金額
    - supplier_summaries: 供應商摘要列表
    """

    total_orders: int = Field(description="採購訂單總數")
    total_amount: Decimal = Field(description="採購總金額")
    completed_orders: int = Field(description="已完成訂單數")
    pending_orders: int = Field(description="待處理訂單數")
    average_order_amount: Decimal = Field(description="平均訂單金額")
    supplier_summaries: List[SupplierSummaryResponse] = Field(
        default=[], description="供應商摘要列表"
    )

    model_config = {"from_attributes": True}


# ==========================================
# 客戶報表模型
# ==========================================
class CustomerLevelDistributionResponse(BaseModel):
    """
    客戶等級分佈回應模型

    提供各客戶等級的人數及佔比統計。

    屬性：
    - level_id: 等級 ID
    - level_name: 等級名稱
    - customer_count: 客戶數量
    - percentage: 佔總客戶數百分比
    """

    level_id: int = Field(description="等級 ID")
    level_name: str = Field(description="等級名稱")
    customer_count: int = Field(description="客戶數量")
    percentage: Decimal = Field(description="佔總客戶數百分比")

    model_config = {"from_attributes": True}


class TopCustomerResponse(BaseModel):
    """
    頂級客戶回應模型

    提供頂級客戶的排名及消費統計資料。

    屬性：
    - rank: 排名
    - customer_id: 客戶 ID
    - member_no: 會員編號
    - customer_name: 客戶名稱
    - level_name: 會員等級名稱
    - total_spent: 總消費金額
    - total_orders: 總訂單數
    - last_purchase_date: 最後消費日期
    """

    rank: int = Field(description="排名")
    customer_id: int = Field(description="客戶 ID")
    member_no: str = Field(description="會員編號")
    customer_name: str = Field(description="客戶名稱")
    level_name: str = Field(description="會員等級名稱")
    total_spent: Decimal = Field(description="總消費金額")
    total_orders: int = Field(description="總訂單數")
    last_purchase_date: Optional[datetime] = Field(
        default=None, description="最後消費日期"
    )

    model_config = {"from_attributes": True}


class CustomerReportResponse(BaseModel):
    """
    客戶報表回應模型

    提供客戶整體統計資料，包含客戶總數、活躍度、消費統計及等級分佈。

    屬性：
    - total_customers: 客戶總數
    - new_customers_this_month: 本月新增客戶數
    - active_customers: 活躍客戶數（近期有消費）
    - dormant_customers: 休眠客戶數（長期未消費）
    - average_customer_spending: 平均客戶消費金額
    - total_points: 總點數餘額
    - vip_customers: VIP 客戶數
    - level_distribution: 客戶等級分佈
    - top_customers: 頂級客戶列表
    """

    total_customers: int = Field(description="客戶總數")
    new_customers_this_month: int = Field(description="本月新增客戶數")
    active_customers: int = Field(description="活躍客戶數（近期有消費）")
    dormant_customers: int = Field(description="休眠客戶數（長期未消費）")
    average_customer_spending: Decimal = Field(description="平均客戶消費金額")
    total_points: int = Field(description="總點數餘額")
    vip_customers: int = Field(description="VIP 客戶數")
    level_distribution: List[CustomerLevelDistributionResponse] = Field(
        default=[], description="客戶等級分佈"
    )
    top_customers: List[TopCustomerResponse] = Field(
        default=[], description="頂級客戶列表"
    )

    model_config = {"from_attributes": True}


# ==========================================
# 利潤分析報表模型
# ==========================================
class RevenueSummaryResponse(BaseModel):
    """
    營收摘要回應模型

    屬性：
    - total_sales: 銷售總額
    - return_amount: 退貨金額
    - discount_amount: 折扣金額
    - net_revenue: 淨營收
    - net_revenue_ratio: 淨營收佔比
    """

    total_sales: Decimal = Field(description="銷售總額")
    return_amount: Decimal = Field(description="退貨金額")
    discount_amount: Decimal = Field(description="折扣金額")
    net_revenue: Decimal = Field(description="淨營收")
    net_revenue_ratio: Decimal = Field(default=Decimal("100.00"), description="淨營收佔比")

    model_config = {"from_attributes": True}


class CostStructureResponse(BaseModel):
    """
    成本結構回應模型

    屬性：
    - cost_of_goods_sold: 銷貨成本
    - cost_ratio: 成本佔比
    - gross_profit: 毛利
    - gross_profit_margin: 毛利率
    """

    cost_of_goods_sold: Decimal = Field(description="銷貨成本")
    cost_ratio: Decimal = Field(description="成本佔比")
    gross_profit: Decimal = Field(description="毛利")
    gross_profit_margin: Decimal = Field(description="毛利率")

    model_config = {"from_attributes": True}


class CategoryProfitResponse(BaseModel):
    """
    分類利潤分析回應模型

    屬性：
    - category_id: 分類 ID
    - category_name: 分類名稱
    - net_sales: 淨銷售額
    - cost: 成本
    - gross_profit: 毛利
    - gross_profit_margin: 毛利率
    - profit_contribution: 佔毛利比
    """

    category_id: Optional[int] = Field(default=None, description="分類 ID")
    category_name: str = Field(description="分類名稱")
    net_sales: Decimal = Field(description="淨銷售額")
    cost: Decimal = Field(description="成本")
    gross_profit: Decimal = Field(description="毛利")
    gross_profit_margin: Decimal = Field(description="毛利率")
    profit_contribution: Decimal = Field(description="佔毛利比")

    model_config = {"from_attributes": True}


class StoreProfitResponse(BaseModel):
    """
    門市利潤分析回應模型

    屬性：
    - store_id: 門市 ID
    - store_name: 門市名稱
    - net_sales: 淨銷售額
    - cost: 成本
    - gross_profit: 毛利
    - gross_profit_margin: 毛利率
    """

    store_id: Optional[int] = Field(default=None, description="門市 ID")
    store_name: str = Field(description="門市名稱")
    net_sales: Decimal = Field(description="淨銷售額")
    cost: Decimal = Field(description="成本")
    gross_profit: Decimal = Field(description="毛利")
    gross_profit_margin: Decimal = Field(description="毛利率")

    model_config = {"from_attributes": True}


class PeriodComparisonResponse(BaseModel):
    """
    同期比較回應模型

    屬性：
    - metric: 指標名稱
    - current_value: 本期數值
    - previous_value: 上期數值
    - change: 增減數值
    - change_rate: 增減百分比
    """

    metric: str = Field(description="指標名稱")
    current_value: Decimal = Field(description="本期數值")
    previous_value: Decimal = Field(description="上期數值")
    change: Decimal = Field(description="增減數值")
    change_rate: Optional[Decimal] = Field(default=None, description="增減百分比")

    model_config = {"from_attributes": True}


class ProfitAnalysisResponse(BaseModel):
    """
    利潤分析報表回應模型

    屬性：
    - period_start: 期間開始日期
    - period_end: 期間結束日期
    - revenue_summary: 營收摘要
    - cost_structure: 成本結構
    - category_profits: 各分類利潤分析
    - store_profits: 各門市利潤分析
    - period_comparison: 同期比較
    """

    period_start: date_type = Field(description="期間開始日期")
    period_end: date_type = Field(description="期間結束日期")
    revenue_summary: RevenueSummaryResponse = Field(description="營收摘要")
    cost_structure: CostStructureResponse = Field(description="成本結構")
    category_profits: List[CategoryProfitResponse] = Field(
        default=[], description="各分類利潤分析"
    )
    store_profits: List[StoreProfitResponse] = Field(
        default=[], description="各門市利潤分析"
    )
    period_comparison: List[PeriodComparisonResponse] = Field(
        default=[], description="同期比較"
    )

    model_config = {"from_attributes": True}


# ==========================================
# 報表匯出模型
# ==========================================
class ReportExportRequest(BaseModel):
    """報表匯出請求模型"""

    report_type: ReportType = Field(description="報表類型")
    format: ExportFormat = Field(description="匯出格式")
    start_date: Optional[date_type] = Field(default=None, description="開始日期")
    end_date: Optional[date_type] = Field(default=None, description="結束日期")
    store_id: Optional[int] = Field(default=None, description="門市 ID")
    include_header: bool = Field(default=True, description="含標題")
    include_filters: bool = Field(default=True, description="含篩選條件")
    include_summary: bool = Field(default=True, description="含合計")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_type": "sales_daily",
                    "format": "csv",
                    "start_date": "2025-12-01",
                    "end_date": "2025-12-31",
                    "include_header": True,
                    "include_filters": True,
                    "include_summary": True,
                }
            ]
        }
    }


# ==========================================
# 期間比較模型
# ==========================================
class ComparisonType(str, Enum):
    """比較類型"""

    YOY = "yoy"  # 年對年 Year over Year
    MOM = "mom"  # 月對月 Month over Month
    WOW = "wow"  # 週對週 Week over Week
    DOD = "dod"  # 日對日 Day over Day
    CUSTOM = "custom"  # 自訂期間


class SalesComparisonItem(BaseModel):
    """銷售比較項目"""

    metric: str = Field(description="指標名稱")
    current_value: Decimal = Field(description="本期數值")
    previous_value: Decimal = Field(description="前期數值")
    change_amount: Decimal = Field(description="變化金額")
    change_rate: Optional[Decimal] = Field(default=None, description="變化率 (%)")


class SalesComparisonResponse(BaseModel):
    """銷售期間比較回應"""

    comparison_type: str = Field(description="比較類型")
    current_period: str = Field(description="本期期間")
    previous_period: str = Field(description="前期期間")
    items: List[SalesComparisonItem] = Field(description="比較項目")


class CustomPeriodComparisonRequest(BaseModel):
    """自訂期間比較請求"""

    period1_start: date_type = Field(description="期間一開始日期")
    period1_end: date_type = Field(description="期間一結束日期")
    period2_start: date_type = Field(description="期間二開始日期")
    period2_end: date_type = Field(description="期間二結束日期")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "period1_start": "2025-01-01",
                    "period1_end": "2025-01-31",
                    "period2_start": "2024-01-01",
                    "period2_end": "2024-01-31",
                }
            ]
        }
    }
