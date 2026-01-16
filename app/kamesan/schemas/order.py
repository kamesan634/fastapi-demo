"""
訂單相關 Schema 模型

定義訂單、訂單明細、付款的請求和回應模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.order import OrderStatus, PaymentMethod, PaymentStatus


# ==========================================
# 訂單明細模型
# ==========================================
class OrderItemCreate(BaseModel):
    """訂單明細建立模型"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(default=1, ge=1, description="數量")
    unit_price: Optional[Decimal] = Field(default=None, ge=0, description="單價（不填則使用商品售價）")
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="折扣金額")


class OrderItemResponse(BaseModel):
    """訂單明細回應模型"""

    id: int = Field(description="明細 ID")
    order_id: int = Field(description="訂單 ID")
    product_id: int = Field(description="商品 ID")
    product_name: str = Field(description="商品名稱")
    quantity: int = Field(description="數量")
    unit_price: Decimal = Field(description="單價")
    discount_amount: Decimal = Field(description="折扣金額")
    subtotal: Decimal = Field(description="小計")
    tax_rate: Decimal = Field(description="稅率")
    tax_amount: Decimal = Field(description="稅額")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


# ==========================================
# 付款模型
# ==========================================
class PaymentCreate(BaseModel):
    """付款建立模型"""

    payment_method: PaymentMethod = Field(description="付款方式")
    amount: Decimal = Field(ge=0, description="付款金額")


class PaymentResponse(BaseModel):
    """付款回應模型"""

    id: int = Field(description="付款 ID")
    order_id: int = Field(description="訂單 ID")
    payment_method: PaymentMethod = Field(description="付款方式")
    amount: Decimal = Field(description="付款金額")
    status: PaymentStatus = Field(description="付款狀態")
    transaction_id: Optional[str] = Field(description="交易編號")
    paid_at: Optional[datetime] = Field(description="付款時間")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


# ==========================================
# 訂單模型
# ==========================================
class OrderCreate(BaseModel):
    """訂單建立模型"""

    store_id: Optional[int] = Field(default=None, description="門市 ID")
    customer_id: Optional[int] = Field(default=None, description="客戶 ID")
    items: List[OrderItemCreate] = Field(min_length=1, description="訂單明細")
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="訂單折扣金額")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    payments: Optional[List[PaymentCreate]] = Field(default=None, description="付款資訊")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "store_id": 1,
                    "customer_id": 1,
                    "items": [
                        {"product_id": 1, "quantity": 2, "discount_amount": "0.00"},
                        {"product_id": 2, "quantity": 1, "discount_amount": "5.00"},
                    ],
                    "discount_amount": "10.00",
                    "notes": "客戶要求分開包裝",
                    "payments": [{"payment_method": "CASH", "amount": "100.00"}],
                }
            ]
        }
    }


class OrderUpdate(BaseModel):
    """訂單更新模型"""

    status: Optional[OrderStatus] = Field(default=None, description="訂單狀態")
    discount_amount: Optional[Decimal] = Field(default=None, ge=0, description="折扣金額")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class OrderResponse(BaseModel):
    """訂單回應模型"""

    id: int = Field(description="訂單 ID")
    order_number: str = Field(description="訂單編號")
    store_id: Optional[int] = Field(description="門市 ID")
    customer_id: Optional[int] = Field(description="客戶 ID")
    status: OrderStatus = Field(description="訂單狀態")
    subtotal: Decimal = Field(description="小計")
    tax_amount: Decimal = Field(description="稅額")
    discount_amount: Decimal = Field(description="折扣金額")
    total_amount: Decimal = Field(description="總金額")
    points_earned: int = Field(description="獲得點數")
    points_used: int = Field(description="使用點數")
    notes: Optional[str] = Field(description="備註")
    order_date: datetime = Field(description="訂單日期")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    items: List[OrderItemResponse] = Field(default=[], description="訂單明細")
    payments: List[PaymentResponse] = Field(default=[], description="付款記錄")

    model_config = {"from_attributes": True}


class OrderSummary(BaseModel):
    """訂單摘要回應模型"""

    id: int = Field(description="訂單 ID")
    order_number: str = Field(description="訂單編號")
    status: OrderStatus = Field(description="訂單狀態")
    total_amount: Decimal = Field(description="總金額")
    order_date: datetime = Field(description="訂單日期")
    customer_name: Optional[str] = Field(description="客戶名稱")
    store_name: Optional[str] = Field(description="門市名稱")

    model_config = {"from_attributes": True}
