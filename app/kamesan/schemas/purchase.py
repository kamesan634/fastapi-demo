"""
採購相關 Schema 模型

定義採購單、驗收單、退貨單、供應商價格的請求和回應模型。

Schema 分類：
- PurchaseOrder: 採購單相關
- PurchaseReceipt: 驗收單相關
- PurchaseReturn: 退貨單相關
- SupplierPrice: 供應商價格相關
- ReplenishmentSuggestion: 補貨建議相關
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.purchase import (
    PurchaseOrderStatus,
    PurchaseReceiptStatus,
    PurchaseReturnStatus,
)


# ==========================================
# 採購單模型
# ==========================================
class PurchaseOrderItemCreate(BaseModel):
    """採購單明細建立模型"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(ge=1, description="採購數量")
    unit_price: Decimal = Field(ge=0, description="單價")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class PurchaseOrderItemResponse(BaseModel):
    """採購單明細回應模型"""

    id: int = Field(description="明細 ID")
    product_id: int = Field(description="商品 ID")
    quantity: int = Field(description="採購數量")
    unit_price: Decimal = Field(description="單價")
    received_quantity: int = Field(description="已收貨數量")
    notes: Optional[str] = Field(description="備註")
    subtotal: Decimal = Field(description="小計")
    pending_quantity: int = Field(description="待收貨數量")

    # 額外資訊
    product_code: Optional[str] = Field(default=None, description="商品代碼")
    product_name: Optional[str] = Field(default=None, description="商品名稱")

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    """採購單建立模型"""

    order_number: Optional[str] = Field(default=None, max_length=30, description="採購單號")
    supplier_id: int = Field(description="供應商 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    order_date: Optional[date] = Field(default=None, description="採購日期")
    expected_date: Optional[date] = Field(default=None, description="預計到貨日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    items: List[PurchaseOrderItemCreate] = Field(description="採購明細")


class PurchaseOrderUpdate(BaseModel):
    """採購單更新模型"""

    expected_date: Optional[date] = Field(default=None, description="預計到貨日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class PurchaseOrderSummary(BaseModel):
    """採購單摘要模型"""

    id: int = Field(description="採購單 ID")
    order_number: str = Field(description="採購單號")
    supplier_id: int = Field(description="供應商 ID")
    supplier_name: Optional[str] = Field(default=None, description="供應商名稱")
    warehouse_id: int = Field(description="倉庫 ID")
    warehouse_name: Optional[str] = Field(default=None, description="倉庫名稱")
    order_date: date = Field(description="採購日期")
    expected_date: Optional[date] = Field(description="預計到貨日期")
    status: PurchaseOrderStatus = Field(description="採購單狀態")
    total_amount: Decimal = Field(description="總金額")
    item_count: int = Field(description="項目數量")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


class PurchaseOrderResponse(BaseModel):
    """採購單回應模型"""

    id: int = Field(description="採購單 ID")
    order_number: str = Field(description="採購單號")
    supplier_id: int = Field(description="供應商 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    order_date: date = Field(description="採購日期")
    expected_date: Optional[date] = Field(description="預計到貨日期")
    status: PurchaseOrderStatus = Field(description="採購單狀態")
    total_amount: Decimal = Field(description="總金額")
    notes: Optional[str] = Field(description="備註")
    approved_by: Optional[int] = Field(description="核准者 ID")
    approved_at: Optional[datetime] = Field(description="核准時間")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    items: List[PurchaseOrderItemResponse] = Field(default=[], description="採購明細")

    model_config = {"from_attributes": True}


# ==========================================
# 驗收單模型
# ==========================================
class PurchaseReceiptItemCreate(BaseModel):
    """驗收單明細建立模型"""

    product_id: int = Field(description="商品 ID")
    purchase_order_item_id: Optional[int] = Field(default=None, description="採購單明細 ID")
    received_quantity: int = Field(ge=0, description="驗收數量")
    rejected_quantity: int = Field(default=0, ge=0, description="退回數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class PurchaseReceiptItemResponse(BaseModel):
    """驗收單明細回應模型"""

    id: int = Field(description="明細 ID")
    product_id: int = Field(description="商品 ID")
    purchase_order_item_id: Optional[int] = Field(description="採購單明細 ID")
    received_quantity: int = Field(description="驗收數量")
    rejected_quantity: int = Field(description="退回數量")
    notes: Optional[str] = Field(description="備註")

    # 額外資訊
    product_code: Optional[str] = Field(default=None, description="商品代碼")
    product_name: Optional[str] = Field(default=None, description="商品名稱")

    model_config = {"from_attributes": True}


class PurchaseReceiptCreate(BaseModel):
    """驗收單建立模型"""

    receipt_number: Optional[str] = Field(default=None, max_length=30, description="驗收單號")
    purchase_order_id: int = Field(description="採購單 ID")
    receipt_date: Optional[date] = Field(default=None, description="驗收日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    items: List[PurchaseReceiptItemCreate] = Field(description="驗收明細")


class PurchaseReceiptSummary(BaseModel):
    """驗收單摘要模型"""

    id: int = Field(description="驗收單 ID")
    receipt_number: str = Field(description="驗收單號")
    purchase_order_id: int = Field(description="採購單 ID")
    purchase_order_number: Optional[str] = Field(default=None, description="採購單號")
    receipt_date: date = Field(description="驗收日期")
    status: PurchaseReceiptStatus = Field(description="驗收單狀態")
    total_quantity: int = Field(description="總驗收數量")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


class PurchaseReceiptResponse(BaseModel):
    """驗收單回應模型"""

    id: int = Field(description="驗收單 ID")
    receipt_number: str = Field(description="驗收單號")
    purchase_order_id: int = Field(description="採購單 ID")
    receipt_date: date = Field(description="驗收日期")
    status: PurchaseReceiptStatus = Field(description="驗收單狀態")
    notes: Optional[str] = Field(description="備註")
    completed_by: Optional[int] = Field(description="完成者 ID")
    completed_at: Optional[datetime] = Field(description="完成時間")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    items: List[PurchaseReceiptItemResponse] = Field(default=[], description="驗收明細")

    model_config = {"from_attributes": True}


# ==========================================
# 退貨單模型
# ==========================================
class PurchaseReturnItemCreate(BaseModel):
    """退貨單明細建立模型"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(ge=1, description="退貨數量")
    unit_price: Decimal = Field(ge=0, description="單價")
    reason: Optional[str] = Field(default=None, max_length=200, description="退貨原因")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class PurchaseReturnItemResponse(BaseModel):
    """退貨單明細回應模型"""

    id: int = Field(description="明細 ID")
    product_id: int = Field(description="商品 ID")
    quantity: int = Field(description="退貨數量")
    unit_price: Decimal = Field(description="單價")
    reason: Optional[str] = Field(description="退貨原因")
    notes: Optional[str] = Field(description="備註")
    subtotal: Decimal = Field(description="小計")

    # 額外資訊
    product_code: Optional[str] = Field(default=None, description="商品代碼")
    product_name: Optional[str] = Field(default=None, description="商品名稱")

    model_config = {"from_attributes": True}


class PurchaseReturnCreate(BaseModel):
    """退貨單建立模型"""

    return_number: Optional[str] = Field(default=None, max_length=30, description="退貨單號")
    supplier_id: int = Field(description="供應商 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    purchase_order_id: Optional[int] = Field(default=None, description="原採購單 ID")
    return_date: Optional[date] = Field(default=None, description="退貨日期")
    reason: Optional[str] = Field(default=None, max_length=200, description="退貨原因")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    items: List[PurchaseReturnItemCreate] = Field(description="退貨明細")


class PurchaseReturnUpdate(BaseModel):
    """退貨單更新模型"""

    reason: Optional[str] = Field(default=None, max_length=200, description="退貨原因")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class PurchaseReturnSummary(BaseModel):
    """退貨單摘要模型"""

    id: int = Field(description="退貨單 ID")
    return_number: str = Field(description="退貨單號")
    supplier_id: int = Field(description="供應商 ID")
    supplier_name: Optional[str] = Field(default=None, description="供應商名稱")
    warehouse_id: int = Field(description="倉庫 ID")
    warehouse_name: Optional[str] = Field(default=None, description="倉庫名稱")
    return_date: date = Field(description="退貨日期")
    status: PurchaseReturnStatus = Field(description="退貨單狀態")
    total_amount: Decimal = Field(description="總金額")
    item_count: int = Field(description="項目數量")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


class PurchaseReturnResponse(BaseModel):
    """退貨單回應模型"""

    id: int = Field(description="退貨單 ID")
    return_number: str = Field(description="退貨單號")
    supplier_id: int = Field(description="供應商 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    purchase_order_id: Optional[int] = Field(description="原採購單 ID")
    return_date: date = Field(description="退貨日期")
    status: PurchaseReturnStatus = Field(description="退貨單狀態")
    total_amount: Decimal = Field(description="總金額")
    reason: Optional[str] = Field(description="退貨原因")
    notes: Optional[str] = Field(description="備註")
    approved_by: Optional[int] = Field(description="核准者 ID")
    approved_at: Optional[datetime] = Field(description="核准時間")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    items: List[PurchaseReturnItemResponse] = Field(default=[], description="退貨明細")

    model_config = {"from_attributes": True}


# ==========================================
# 供應商價格模型
# ==========================================
class SupplierPriceCreate(BaseModel):
    """
    供應商價格建立模型

    用於新增供應商報價。
    """

    supplier_id: int = Field(description="供應商 ID")
    product_id: int = Field(description="商品 ID")
    unit_price: Decimal = Field(ge=0, description="單價")
    min_order_quantity: int = Field(default=1, ge=1, description="最小訂購數量")
    lead_time_days: int = Field(default=1, ge=0, description="交貨天數")
    effective_date: Optional[date] = Field(default=None, description="生效日期")
    expiry_date: Optional[date] = Field(default=None, description="失效日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "supplier_id": 1,
                    "product_id": 1,
                    "unit_price": 100.00,
                    "min_order_quantity": 10,
                    "lead_time_days": 3,
                    "effective_date": "2025-01-01",
                    "expiry_date": "2025-12-31",
                    "notes": "特約價格",
                }
            ]
        }
    }


class SupplierPriceUpdate(BaseModel):
    """
    供應商價格更新模型

    用於更新供應商報價資訊。
    """

    unit_price: Optional[Decimal] = Field(default=None, ge=0, description="單價")
    min_order_quantity: Optional[int] = Field(default=None, ge=1, description="最小訂購數量")
    lead_time_days: Optional[int] = Field(default=None, ge=0, description="交貨天數")
    effective_date: Optional[date] = Field(default=None, description="生效日期")
    expiry_date: Optional[date] = Field(default=None, description="失效日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class SupplierPriceResponse(BaseModel):
    """
    供應商價格回應模型

    回傳供應商報價的完整資訊。
    """

    id: int = Field(description="報價 ID")
    supplier_id: int = Field(description="供應商 ID")
    product_id: int = Field(description="商品 ID")
    unit_price: Decimal = Field(description="單價")
    min_order_quantity: int = Field(description="最小訂購數量")
    lead_time_days: int = Field(description="交貨天數")
    effective_date: date = Field(description="生效日期")
    expiry_date: Optional[date] = Field(description="失效日期")
    notes: Optional[str] = Field(description="備註")
    is_active: bool = Field(description="是否啟用")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 額外資訊
    supplier_name: Optional[str] = Field(default=None, description="供應商名稱")
    product_name: Optional[str] = Field(default=None, description="商品名稱")
    product_code: Optional[str] = Field(default=None, description="商品代碼")

    model_config = {"from_attributes": True}


# ==========================================
# 補貨建議模型
# ==========================================
class ReplenishmentSuggestionResponse(BaseModel):
    """
    補貨建議回應模型

    提供需要補貨的商品及建議的採購資訊。
    """

    product_id: int = Field(description="商品 ID")
    product_code: str = Field(description="商品代碼")
    product_name: str = Field(description="商品名稱")
    warehouse_id: int = Field(description="倉庫 ID")
    warehouse_name: str = Field(description="倉庫名稱")
    current_quantity: int = Field(description="目前庫存")
    min_stock: int = Field(description="最低庫存")
    max_stock: int = Field(description="最高庫存")
    shortage_quantity: int = Field(description="短缺數量")
    suggested_quantity: int = Field(description="建議補貨數量")

    # 最佳供應商資訊
    suggested_supplier_id: Optional[int] = Field(default=None, description="建議供應商 ID")
    suggested_supplier_name: Optional[str] = Field(default=None, description="建議供應商名稱")
    unit_price: Optional[Decimal] = Field(default=None, description="單價")
    lead_time_days: Optional[int] = Field(default=None, description="交貨天數")
    estimated_cost: Optional[Decimal] = Field(default=None, description="預估成本")

    model_config = {"from_attributes": True}
