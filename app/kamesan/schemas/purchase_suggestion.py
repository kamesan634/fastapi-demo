"""
採購建議 Schema

定義採購建議的請求與回應格式。
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SuggestionMethod(str, Enum):
    """建議計算方式"""

    BY_PRODUCT = "BY_PRODUCT"  # 依商品
    BY_CATEGORY = "BY_CATEGORY"  # 依分類
    BY_SUPPLIER = "BY_SUPPLIER"  # 依供應商
    LOW_STOCK = "LOW_STOCK"  # 低於安全庫存
    BY_WAREHOUSE = "BY_WAREHOUSE"  # 依倉庫


class PurchaseSuggestionRequest(BaseModel):
    """採購建議請求"""

    method: SuggestionMethod = Field(
        default=SuggestionMethod.LOW_STOCK,
        description="建議計算方式",
    )
    supplier_id: Optional[int] = Field(default=None, description="供應商 ID")
    category_id: Optional[int] = Field(default=None, description="類別 ID")
    warehouse_id: Optional[int] = Field(default=None, description="倉庫 ID")
    product_id: Optional[int] = Field(default=None, description="商品 ID")
    forecast_days: int = Field(default=7, ge=1, le=90, description="預估銷售天數")
    include_in_transit: bool = Field(default=True, description="是否考慮在途庫存")


class PurchaseSuggestionItem(BaseModel):
    """採購建議項目"""

    product_id: int = Field(description="商品 ID")
    product_code: str = Field(description="商品代碼")
    product_name: str = Field(description="商品名稱")
    supplier_id: Optional[int] = Field(default=None, description="供應商 ID")
    supplier_name: Optional[str] = Field(default=None, description="供應商名稱")
    category_id: Optional[int] = Field(default=None, description="類別 ID")
    category_name: Optional[str] = Field(default=None, description="類別名稱")
    current_stock: int = Field(description="現有庫存")
    safety_stock: int = Field(description="安全庫存")
    shortage: int = Field(description="缺口（安全庫存 - 現有庫存）")
    in_transit: int = Field(description="在途庫存")
    forecast_sales: int = Field(description="預估銷售量")
    suggested_quantity: int = Field(description="建議採購數量")
    unit_price: Decimal = Field(description="單價")
    suggested_amount: Decimal = Field(description="建議金額")
    min_order_quantity: int = Field(default=1, description="最小訂購量")

    model_config = {"from_attributes": True}


class PurchaseSuggestionSummary(BaseModel):
    """採購建議摘要"""

    total_items: int = Field(description="商品項數")
    total_quantity: int = Field(description="總建議數量")
    total_amount: Decimal = Field(description="總建議金額")
    suppliers_count: int = Field(description="供應商數量")


class PurchaseSuggestionResponse(BaseModel):
    """採購建議回應"""

    generated_at: datetime = Field(description="產生時間")
    method: SuggestionMethod = Field(description="計算方式")
    forecast_days: int = Field(description="預估天數")
    items: List[PurchaseSuggestionItem] = Field(description="建議項目")
    summary: PurchaseSuggestionSummary = Field(description="摘要")


class ConvertToOrderItem(BaseModel):
    """轉採購單項目"""

    product_id: int = Field(description="商品 ID")
    supplier_id: int = Field(description="供應商 ID")
    quantity: int = Field(ge=1, description="採購數量")
    unit_price: Optional[Decimal] = Field(default=None, description="單價（可覆蓋）")


class ConvertToOrderRequest(BaseModel):
    """轉採購單請求"""

    items: List[ConvertToOrderItem] = Field(min_length=1, description="採購項目")
    expected_date: date = Field(description="預計到貨日")
    warehouse_id: int = Field(description="入庫倉庫 ID")
    group_by_supplier: bool = Field(default=True, description="是否依供應商分組")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class ConvertToOrderResponse(BaseModel):
    """轉採購單回應"""

    created_orders: List[int] = Field(description="建立的採購單 ID 列表")
    order_numbers: List[str] = Field(description="建立的採購單號列表")
    total_amount: Decimal = Field(description="總金額")
    message: str = Field(description="訊息")
