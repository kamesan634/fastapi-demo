"""
銷售退貨相關 Schema 模型

定義銷售退貨的請求和回應模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.order import ReturnReason, SalesReturnStatus


# ==========================================
# 退貨明細模型
# ==========================================
class SalesReturnItemCreate(BaseModel):
    """退貨明細建立模型"""

    order_item_id: Optional[int] = Field(
        default=None, description="原訂單明細 ID（若有）"
    )
    product_id: int = Field(description="商品 ID")
    quantity: int = Field(default=1, ge=1, description="退貨數量")
    unit_price: Optional[Decimal] = Field(
        default=None, ge=0, description="單價（不填則使用原訂單價格）"
    )


class SalesReturnItemResponse(BaseModel):
    """退貨明細回應模型"""

    id: int = Field(description="明細 ID")
    sales_return_id: int = Field(description="退貨單 ID")
    order_item_id: Optional[int] = Field(description="原訂單明細 ID")
    product_id: int = Field(description="商品 ID")
    product_name: str = Field(description="商品名稱")
    quantity: int = Field(description="退貨數量")
    unit_price: Decimal = Field(description="單價")
    subtotal: Decimal = Field(description="小計")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


# ==========================================
# 退貨單模型
# ==========================================
class SalesReturnCreate(BaseModel):
    """退貨單建立模型"""

    order_id: int = Field(description="原訂單 ID")
    reason: ReturnReason = Field(description="退貨原因")
    reason_detail: Optional[str] = Field(
        default=None, max_length=500, description="退貨原因說明"
    )
    items: List[SalesReturnItemCreate] = Field(
        min_length=1, description="退貨明細"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="備註"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "order_id": 1,
                    "reason": "DEFECTIVE",
                    "reason_detail": "商品有瑕疵",
                    "items": [
                        {"order_item_id": 1, "product_id": 1, "quantity": 1}
                    ],
                    "notes": "客戶要求全額退款",
                }
            ]
        }
    }


class SalesReturnUpdate(BaseModel):
    """退貨單更新模型"""

    status: Optional[SalesReturnStatus] = Field(
        default=None, description="退貨狀態"
    )
    reason: Optional[ReturnReason] = Field(
        default=None, description="退貨原因"
    )
    reason_detail: Optional[str] = Field(
        default=None, max_length=500, description="退貨原因說明"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="備註"
    )


class SalesReturnResponse(BaseModel):
    """退貨單回應模型"""

    id: int = Field(description="退貨單 ID")
    return_number: str = Field(description="退貨單號")
    order_id: int = Field(description="原訂單 ID")
    store_id: Optional[int] = Field(description="門市 ID")
    customer_id: Optional[int] = Field(description="客戶 ID")
    status: SalesReturnStatus = Field(description="退貨狀態")
    reason: ReturnReason = Field(description="退貨原因")
    reason_detail: Optional[str] = Field(description="退貨原因說明")
    total_amount: Decimal = Field(description="退款金額")
    points_deducted: int = Field(description="扣除點數")
    notes: Optional[str] = Field(description="備註")
    return_date: datetime = Field(description="退貨日期")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    items: List[SalesReturnItemResponse] = Field(
        default=[], description="退貨明細"
    )

    model_config = {"from_attributes": True}


class SalesReturnSummary(BaseModel):
    """退貨單摘要回應模型"""

    id: int = Field(description="退貨單 ID")
    return_number: str = Field(description="退貨單號")
    order_id: int = Field(description="原訂單 ID")
    status: SalesReturnStatus = Field(description="退貨狀態")
    reason: ReturnReason = Field(description="退貨原因")
    total_amount: Decimal = Field(description="退款金額")
    return_date: datetime = Field(description="退貨日期")

    model_config = {"from_attributes": True}


class SalesReturnApproveRequest(BaseModel):
    """退貨核准請求模型"""

    notes: Optional[str] = Field(
        default=None, max_length=500, description="核准備註"
    )


class SalesReturnRejectRequest(BaseModel):
    """退貨拒絕請求模型"""

    reason: str = Field(max_length=500, description="拒絕原因")
