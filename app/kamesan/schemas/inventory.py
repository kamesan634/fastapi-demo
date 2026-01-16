"""
庫存相關 Schema 模型

定義庫存和庫存異動的請求和回應模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.kamesan.models.inventory import TransactionType


class InventoryBase(BaseModel):
    """庫存基礎模型"""

    product_id: int = Field(description="商品 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    quantity: int = Field(default=0, ge=0, description="庫存數量")


class InventoryResponse(InventoryBase):
    """庫存回應模型"""

    id: int = Field(description="庫存 ID")
    reserved_quantity: int = Field(description="保留數量")
    available_quantity: int = Field(description="可用數量")
    last_stock_date: Optional[datetime] = Field(description="最後盤點日期")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


class InventoryAdjustRequest(BaseModel):
    """庫存調整請求模型"""

    product_id: int = Field(description="商品 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    quantity: int = Field(description="調整數量（正數=入庫, 負數=出庫）")
    reason: Optional[str] = Field(default=None, max_length=200, description="調整原因")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_id": 1,
                    "warehouse_id": 1,
                    "quantity": 10,
                    "reason": "進貨入庫",
                }
            ]
        }
    }


class InventoryAdjustByIdRequest(BaseModel):
    """依庫存 ID 調整庫存請求模型"""

    quantity: int = Field(description="調整數量（正數=入庫, 負數=出庫）")
    reason: Optional[str] = Field(default=None, max_length=200, description="調整原因")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "quantity": 10,
                    "reason": "進貨入庫",
                }
            ]
        }
    }


class InventoryTransactionResponse(BaseModel):
    """庫存異動記錄回應模型"""

    id: int = Field(description="異動 ID")
    product_id: int = Field(description="商品 ID")
    warehouse_id: int = Field(description="倉庫 ID")
    transaction_type: TransactionType = Field(description="異動類型")
    quantity: int = Field(description="異動數量")
    before_quantity: int = Field(description="異動前數量")
    after_quantity: int = Field(description="異動後數量")
    reference_type: Optional[str] = Field(description="參考單據類型")
    reference_id: Optional[int] = Field(description="參考單據 ID")
    notes: Optional[str] = Field(description="備註")
    created_by: Optional[int] = Field(description="建立者 ID")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


class LowStockResponse(BaseModel):
    """低庫存商品回應模型"""

    product_id: int = Field(description="商品 ID")
    product_code: str = Field(description="商品代碼")
    product_name: str = Field(description="商品名稱")
    warehouse_id: int = Field(description="倉庫 ID")
    warehouse_name: str = Field(description="倉庫名稱")
    current_quantity: int = Field(description="目前庫存")
    min_stock: int = Field(description="最低庫存")
    shortage: int = Field(description="短缺數量")
