"""
庫存盤點與調撥相關 Schema 模型

定義庫存盤點、盤點明細、庫存調撥、調撥明細的請求和回應模型。

Schema 分類：
- StockCount: 庫存盤點單相關
- StockCountItem: 盤點明細相關
- StockTransfer: 庫存調撥單相關
- StockTransferItem: 調撥明細相關
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.kamesan.models.stock import StockCountStatus, StockTransferStatus


# ==========================================
# 庫存盤點明細模型
# ==========================================
class StockCountItemCreate(BaseModel):
    """
    庫存盤點明細建立模型

    用於建立盤點單時新增盤點項目。
    """

    product_id: int = Field(description="商品 ID")
    system_quantity: int = Field(ge=0, description="系統數量")
    actual_quantity: int = Field(ge=0, description="實際數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_id": 1,
                    "system_quantity": 100,
                    "actual_quantity": 98,
                    "notes": "有 2 件破損報廢",
                }
            ]
        }
    }


class StockCountItemUpdate(BaseModel):
    """
    庫存盤點明細更新模型

    用於更新盤點項目的實際數量和備註。
    """

    actual_quantity: Optional[int] = Field(default=None, ge=0, description="實際數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class StockCountItemResponse(BaseModel):
    """
    庫存盤點明細回應模型

    回傳盤點項目的完整資訊。
    """

    id: int = Field(description="明細 ID")
    stock_count_id: int = Field(description="盤點單 ID")
    product_id: int = Field(description="商品 ID")
    system_quantity: int = Field(description="系統數量")
    actual_quantity: int = Field(description="實際數量")
    difference: int = Field(description="差異數量")
    notes: Optional[str] = Field(description="備註")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 庫存盤點單模型
# ==========================================
class StockCountCreate(BaseModel):
    """
    庫存盤點單建立模型

    用於建立新的盤點單。
    """

    count_number: Optional[str] = Field(default=None, max_length=30, description="盤點單號（不填則自動產生）")
    warehouse_id: int = Field(description="倉庫 ID")
    count_date: Optional[date] = Field(default=None, description="盤點日期（不填則使用今天）")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    items: Optional[List[StockCountItemCreate]] = Field(default=None, description="盤點明細")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "count_number": "SC20250107001",
                    "warehouse_id": 1,
                    "count_date": "2025-01-07",
                    "notes": "年度盤點",
                    "items": [
                        {
                            "product_id": 1,
                            "system_quantity": 100,
                            "actual_quantity": 98,
                            "notes": "有 2 件破損",
                        }
                    ],
                }
            ]
        }
    }


class StockCountUpdate(BaseModel):
    """
    庫存盤點單更新模型

    用於更新盤點單狀態和備註。
    """

    status: Optional[StockCountStatus] = Field(default=None, description="盤點狀態")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class StockCountResponse(BaseModel):
    """
    庫存盤點單回應模型

    回傳盤點單的完整資訊，包含明細。
    """

    id: int = Field(description="盤點單 ID")
    count_number: str = Field(description="盤點單號")
    warehouse_id: int = Field(description="倉庫 ID")
    count_date: date = Field(description="盤點日期")
    status: StockCountStatus = Field(description="盤點狀態")
    notes: Optional[str] = Field(description="備註")
    created_by: Optional[int] = Field(description="建立者 ID")
    completed_by: Optional[int] = Field(description="完成者 ID")
    completed_at: Optional[datetime] = Field(description="完成時間")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    items: List[StockCountItemResponse] = Field(default=[], description="盤點明細")

    # 計算欄位
    item_count: int = Field(default=0, description="盤點項目數量")
    total_difference: int = Field(default=0, description="總差異數量")

    model_config = {"from_attributes": True}


class StockCountSummary(BaseModel):
    """
    庫存盤點單摘要模型

    用於列表顯示的簡略資訊。
    """

    id: int = Field(description="盤點單 ID")
    count_number: str = Field(description="盤點單號")
    warehouse_id: int = Field(description="倉庫 ID")
    warehouse_name: Optional[str] = Field(default=None, description="倉庫名稱")
    count_date: date = Field(description="盤點日期")
    status: StockCountStatus = Field(description="盤點狀態")
    item_count: int = Field(description="盤點項目數量")
    total_difference: int = Field(description="總差異數量")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


# ==========================================
# 庫存調撥明細模型
# ==========================================
class StockTransferItemCreate(BaseModel):
    """
    庫存調撥明細建立模型

    用於建立調撥單時新增調撥項目。
    """

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(gt=0, description="調撥數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_id": 1,
                    "quantity": 50,
                    "notes": "補充門市庫存",
                }
            ]
        }
    }


class StockTransferItemUpdate(BaseModel):
    """
    庫存調撥明細更新模型

    用於更新調撥項目的數量和備註。
    """

    quantity: Optional[int] = Field(default=None, gt=0, description="調撥數量")
    received_quantity: Optional[int] = Field(default=None, ge=0, description="實際收貨數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class StockTransferItemResponse(BaseModel):
    """
    庫存調撥明細回應模型

    回傳調撥項目的完整資訊。
    """

    id: int = Field(description="明細 ID")
    stock_transfer_id: int = Field(description="調撥單 ID")
    product_id: int = Field(description="商品 ID")
    quantity: int = Field(description="調撥數量")
    received_quantity: Optional[int] = Field(description="實際收貨數量")
    shortage: int = Field(default=0, description="短少數量")
    notes: Optional[str] = Field(description="備註")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 庫存調撥單模型
# ==========================================
class StockTransferCreate(BaseModel):
    """
    庫存調撥單建立模型

    用於建立新的調撥單。
    """

    transfer_number: Optional[str] = Field(default=None, max_length=30, description="調撥單號（不填則自動產生）")
    source_warehouse_id: int = Field(description="來源倉庫 ID")
    destination_warehouse_id: int = Field(description="目的倉庫 ID")
    transfer_date: Optional[date] = Field(default=None, description="調撥日期（不填則使用今天）")
    expected_date: Optional[date] = Field(default=None, description="預計到達日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    items: List[StockTransferItemCreate] = Field(min_length=1, description="調撥明細")

    @field_validator("destination_warehouse_id")
    @classmethod
    def validate_different_warehouses(cls, v: int, info) -> int:
        """驗證來源和目的倉庫不同"""
        source_id = info.data.get("source_warehouse_id")
        if source_id is not None and v == source_id:
            raise ValueError("來源倉庫和目的倉庫不能相同")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transfer_number": "ST20250107001",
                    "source_warehouse_id": 1,
                    "destination_warehouse_id": 2,
                    "transfer_date": "2025-01-07",
                    "expected_date": "2025-01-08",
                    "notes": "緊急調貨",
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": 50,
                            "notes": "補充門市庫存",
                        }
                    ],
                }
            ]
        }
    }


class StockTransferUpdate(BaseModel):
    """
    庫存調撥單更新模型

    用於更新調撥單狀態、日期和備註。
    """

    status: Optional[StockTransferStatus] = Field(default=None, description="調撥狀態")
    expected_date: Optional[date] = Field(default=None, description="預計到達日期")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")


class StockTransferResponse(BaseModel):
    """
    庫存調撥單回應模型

    回傳調撥單的完整資訊，包含明細。
    """

    id: int = Field(description="調撥單 ID")
    transfer_number: str = Field(description="調撥單號")
    source_warehouse_id: int = Field(description="來源倉庫 ID")
    destination_warehouse_id: int = Field(description="目的倉庫 ID")
    transfer_date: date = Field(description="調撥日期")
    expected_date: Optional[date] = Field(description="預計到達日期")
    received_date: Optional[date] = Field(description="實際收貨日期")
    status: StockTransferStatus = Field(description="調撥狀態")
    notes: Optional[str] = Field(description="備註")
    created_by: Optional[int] = Field(description="建立者 ID")
    approved_by: Optional[int] = Field(description="核准者 ID")
    approved_at: Optional[datetime] = Field(description="核准時間")
    received_by: Optional[int] = Field(description="收貨者 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    items: List[StockTransferItemResponse] = Field(default=[], description="調撥明細")

    # 計算欄位
    item_count: int = Field(default=0, description="調撥項目數量")
    total_quantity: int = Field(default=0, description="總調撥數量")
    total_received_quantity: int = Field(default=0, description="總收貨數量")

    model_config = {"from_attributes": True}


class StockTransferSummary(BaseModel):
    """
    庫存調撥單摘要模型

    用於列表顯示的簡略資訊。
    """

    id: int = Field(description="調撥單 ID")
    transfer_number: str = Field(description="調撥單號")
    source_warehouse_id: int = Field(description="來源倉庫 ID")
    source_warehouse_name: Optional[str] = Field(default=None, description="來源倉庫名稱")
    destination_warehouse_id: int = Field(description="目的倉庫 ID")
    destination_warehouse_name: Optional[str] = Field(default=None, description="目的倉庫名稱")
    transfer_date: date = Field(description="調撥日期")
    status: StockTransferStatus = Field(description="調撥狀態")
    item_count: int = Field(description="調撥項目數量")
    total_quantity: int = Field(description="總調撥數量")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


# ==========================================
# 操作請求模型
# ==========================================
class StockCountStartRequest(BaseModel):
    """開始盤點請求模型"""

    pass


class StockCountCompleteRequest(BaseModel):
    """完成盤點請求模型"""

    completed_by: int = Field(description="完成者 ID")


class StockTransferSubmitRequest(BaseModel):
    """提交調撥單請求模型"""

    pass


class StockTransferApproveRequest(BaseModel):
    """核准調撥單請求模型"""

    approved_by: int = Field(description="核准者 ID")


class StockTransferShipRequest(BaseModel):
    """出貨請求模型"""

    pass


class StockTransferReceiveRequest(BaseModel):
    """收貨請求模型"""

    received_by: int = Field(description="收貨者 ID")
    items: Optional[List[StockTransferItemUpdate]] = Field(
        default=None,
        description="更新收貨數量的明細列表",
    )
