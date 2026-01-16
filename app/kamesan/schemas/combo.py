"""
商品組合/套餐 Schema

定義商品組合與套餐的請求與回應格式。
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ComboType(str, Enum):
    """組合類型"""

    FIXED = "FIXED"  # 固定組合
    FLEXIBLE = "FLEXIBLE"  # 自選組合


# ==========================================
# 組合項目 Schema
# ==========================================
class ComboItemBase(BaseModel):
    """組合項目基礎 Schema"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(default=1, ge=1, description="數量")
    is_required: bool = Field(default=True, description="是否必選")
    is_default: bool = Field(default=False, description="是否預設選擇")
    sort_order: int = Field(default=0, description="排序順序")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class ComboItemCreate(ComboItemBase):
    """組合項目建立 Schema"""

    pass


class ComboItemUpdate(BaseModel):
    """組合項目更新 Schema"""

    quantity: Optional[int] = Field(default=None, ge=1, description="數量")
    is_required: Optional[bool] = Field(default=None, description="是否必選")
    is_default: Optional[bool] = Field(default=None, description="是否預設選擇")
    sort_order: Optional[int] = Field(default=None, description="排序順序")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")


class ComboItemResponse(ComboItemBase):
    """組合項目回應 Schema"""

    id: int
    combo_id: int
    product_name: Optional[str] = Field(None, description="商品名稱")
    product_code: Optional[str] = Field(None, description="商品代碼")
    product_price: Optional[Decimal] = Field(None, description="商品單價")
    subtotal: Optional[Decimal] = Field(None, description="小計")

    model_config = {"from_attributes": True}


# ==========================================
# 組合 Schema
# ==========================================
class ComboBase(BaseModel):
    """組合基礎 Schema"""

    code: str = Field(max_length=30, description="組合編號")
    name: str = Field(max_length=100, description="組合名稱")
    combo_type: ComboType = Field(default=ComboType.FIXED, description="組合類型")
    combo_price: Decimal = Field(ge=0, description="組合售價")
    original_price: Decimal = Field(ge=0, description="原價總計")
    min_select_count: Optional[int] = Field(default=None, ge=1, description="最少選擇數量")
    max_select_count: Optional[int] = Field(default=None, ge=1, description="最多選擇數量")
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")
    description: Optional[str] = Field(default=None, max_length=500, description="描述")
    image_url: Optional[str] = Field(default=None, max_length=500, description="圖片 URL")

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v, info):
        """驗證結束日期"""
        if v is not None:
            start = info.data.get("start_date")
            if start is not None and v < start:
                raise ValueError("結束日期不可早於開始日期")
        return v


class ComboCreate(ComboBase):
    """組合建立 Schema"""

    items: List[ComboItemCreate] = Field(min_length=1, description="組合項目")


class ComboUpdate(BaseModel):
    """組合更新 Schema"""

    name: Optional[str] = Field(default=None, max_length=100, description="組合名稱")
    combo_type: Optional[ComboType] = Field(default=None, description="組合類型")
    combo_price: Optional[Decimal] = Field(default=None, ge=0, description="組合售價")
    original_price: Optional[Decimal] = Field(default=None, ge=0, description="原價總計")
    min_select_count: Optional[int] = Field(default=None, ge=1, description="最少選擇數量")
    max_select_count: Optional[int] = Field(default=None, ge=1, description="最多選擇數量")
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")
    description: Optional[str] = Field(default=None, max_length=500, description="描述")
    image_url: Optional[str] = Field(default=None, max_length=500, description="圖片 URL")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class ComboResponse(ComboBase):
    """組合回應 Schema"""

    id: int
    is_active: bool
    savings: Decimal = Field(description="節省金額")
    discount_percentage: Decimal = Field(description="折扣百分比")
    is_valid: bool = Field(description="是否在有效期內")
    items: List[ComboItemResponse] = Field(default=[], description="組合項目")
    item_count: int = Field(description="項目數量")

    model_config = {"from_attributes": True}


class ComboSummaryResponse(BaseModel):
    """組合摘要回應 Schema"""

    id: int
    code: str
    name: str
    combo_type: ComboType
    combo_price: Decimal
    original_price: Decimal
    savings: Decimal
    is_active: bool
    is_valid: bool
    item_count: int

    model_config = {"from_attributes": True}


# ==========================================
# 組合計算 Schema
# ==========================================
class ComboSelectionItem(BaseModel):
    """組合選擇項目"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(default=1, ge=1, description="數量")


class ComboCalculateRequest(BaseModel):
    """組合價格計算請求"""

    combo_id: int = Field(description="組合 ID")
    selections: Optional[List[ComboSelectionItem]] = Field(
        default=None, description="選擇的商品（自選組合用）"
    )


class ComboCalculateResponse(BaseModel):
    """組合價格計算回應"""

    combo_id: int
    combo_name: str
    combo_price: Decimal
    original_price: Decimal
    savings: Decimal
    discount_percentage: Decimal
    is_valid: bool
    selected_items: List[ComboItemResponse]
