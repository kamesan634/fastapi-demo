"""
供應商價格管理增強 Schema

提供供應商價格比較、批量操作等功能的 Schema。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ==========================================
# 價格比較 Schema
# ==========================================
class PriceComparisonItem(BaseModel):
    """價格比較項目"""

    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    min_order_quantity: int
    lead_time_days: int
    is_valid: bool
    price_rank: int = Field(description="價格排名（1 為最低價）")
    price_diff_percent: Optional[Decimal] = Field(
        None, description="與最低價差異百分比"
    )


class PriceComparisonResponse(BaseModel):
    """價格比較回應"""

    product_id: int
    product_code: str
    product_name: str
    lowest_price: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None
    average_price: Optional[Decimal] = None
    supplier_count: int
    comparison: List[PriceComparisonItem]


# ==========================================
# 批量操作 Schema
# ==========================================
class SupplierPriceBulkItem(BaseModel):
    """批量供應商價格項目"""

    supplier_id: int = Field(description="供應商 ID")
    product_id: int = Field(description="商品 ID")
    unit_price: Decimal = Field(ge=0, description="單價")
    min_order_quantity: int = Field(default=1, ge=1, description="最小訂購數量")
    lead_time_days: int = Field(default=1, ge=0, description="交貨天數")
    effective_date: Optional[date] = Field(default=None, description="生效日期")
    expiry_date: Optional[date] = Field(default=None, description="失效日期")


class SupplierPriceBulkCreateRequest(BaseModel):
    """批量建立供應商價格請求"""

    items: List[SupplierPriceBulkItem] = Field(
        min_length=1, max_length=500, description="價格項目列表"
    )
    update_existing: bool = Field(
        default=False, description="是否更新已存在的價格（依供應商+商品）"
    )


class SupplierPriceBulkCreateResult(BaseModel):
    """批量建立結果"""

    created_count: int = Field(description="新建數量")
    updated_count: int = Field(description="更新數量")
    error_count: int = Field(description="錯誤數量")
    errors: List[str] = Field(default=[], description="錯誤訊息")


class SupplierPriceImportRow(BaseModel):
    """供應商價格匯入列"""

    supplier_code: str = Field(description="供應商代碼")
    product_code: str = Field(description="商品代碼")
    unit_price: Decimal = Field(ge=0, description="單價")
    min_order_quantity: int = Field(default=1, ge=1, description="最小訂購數量")
    lead_time_days: int = Field(default=1, ge=0, description="交貨天數")
    effective_date: Optional[str] = Field(default=None, description="生效日期 (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(default=None, description="失效日期 (YYYY-MM-DD)")


class SupplierPriceImportRequest(BaseModel):
    """供應商價格匯入請求"""

    rows: List[SupplierPriceImportRow] = Field(
        min_length=1, max_length=1000, description="匯入資料"
    )
    update_existing: bool = Field(
        default=False, description="是否更新已存在的價格"
    )


class SupplierPriceImportResult(BaseModel):
    """供應商價格匯入結果"""

    total_rows: int
    success_count: int
    error_count: int
    errors: List[dict] = Field(default=[], description="錯誤詳情")


# ==========================================
# 價格到期提醒 Schema
# ==========================================
class ExpiringPriceResponse(BaseModel):
    """即將到期的價格"""

    id: int
    supplier_id: int
    supplier_name: str
    product_id: int
    product_code: str
    product_name: str
    unit_price: Decimal
    expiry_date: date
    days_until_expiry: int


class ExpiringPricesListResponse(BaseModel):
    """即將到期價格列表"""

    items: List[ExpiringPriceResponse]
    total_count: int
    expiring_within_days: int


# ==========================================
# 價格歷史 Schema
# ==========================================
class PriceHistoryEntry(BaseModel):
    """價格歷史記錄"""

    id: int
    unit_price: Decimal
    min_order_quantity: int
    lead_time_days: int
    effective_date: date
    expiry_date: Optional[date]
    is_active: bool
    created_at: datetime
    created_by: Optional[int]


class PriceHistoryResponse(BaseModel):
    """價格歷史回應"""

    supplier_id: int
    supplier_name: str
    product_id: int
    product_code: str
    product_name: str
    current_price: Optional[Decimal]
    history: List[PriceHistoryEntry]


# ==========================================
# 價格調整 Schema
# ==========================================
class PriceAdjustmentRequest(BaseModel):
    """價格調整請求"""

    supplier_id: int = Field(description="供應商 ID")
    adjustment_type: str = Field(
        description="調整類型: 'percentage' 或 'fixed'"
    )
    adjustment_value: Decimal = Field(
        description="調整值（百分比為 0-100，固定金額為實際金額）"
    )
    product_ids: Optional[List[int]] = Field(
        default=None, description="指定商品 ID（None 表示全部）"
    )
    new_effective_date: Optional[date] = Field(
        default=None, description="新生效日期"
    )


class PriceAdjustmentPreview(BaseModel):
    """價格調整預覽"""

    product_id: int
    product_code: str
    product_name: str
    current_price: Decimal
    new_price: Decimal
    difference: Decimal


class PriceAdjustmentPreviewResponse(BaseModel):
    """價格調整預覽回應"""

    affected_count: int
    previews: List[PriceAdjustmentPreview]


class PriceAdjustmentResult(BaseModel):
    """價格調整結果"""

    adjusted_count: int
    new_effective_date: date
