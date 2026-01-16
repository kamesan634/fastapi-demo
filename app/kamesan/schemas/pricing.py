"""
價格管理 Schema

定義量販價與促銷價的請求與回應格式。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ==========================================
# 量販價 Schema
# ==========================================
class VolumePricingBase(BaseModel):
    """量販價基礎 Schema"""

    min_quantity: int = Field(ge=1, description="最低數量")
    max_quantity: Optional[int] = Field(default=None, ge=1, description="最高數量")
    unit_price: Decimal = Field(ge=0, description="單價")

    @field_validator("max_quantity", mode="before")
    @classmethod
    def validate_max_quantity(cls, v, info):
        """驗證最高數量必須大於最低數量"""
        if v is not None:
            min_qty = info.data.get("min_quantity")
            if min_qty is not None and v < min_qty:
                raise ValueError("最高數量必須大於或等於最低數量")
        return v


class VolumePricingCreate(VolumePricingBase):
    """量販價建立 Schema"""

    pass


class VolumePricingUpdate(BaseModel):
    """量販價更新 Schema"""

    min_quantity: Optional[int] = Field(default=None, ge=1, description="最低數量")
    max_quantity: Optional[int] = Field(default=None, ge=1, description="最高數量")
    unit_price: Optional[Decimal] = Field(default=None, ge=0, description="單價")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class VolumePricingResponse(VolumePricingBase):
    """量販價回應 Schema"""

    id: int
    product_id: int
    is_active: bool

    model_config = {"from_attributes": True}


class VolumePricingTier(BaseModel):
    """量販價階層顯示 Schema"""

    tier: int = Field(description="階層序號")
    quantity_range: str = Field(description="數量範圍描述")
    min_quantity: int
    max_quantity: Optional[int]
    unit_price: Decimal
    discount_percentage: Optional[Decimal] = Field(None, description="折扣百分比")


class ProductVolumePricingResponse(BaseModel):
    """商品量販價完整回應 Schema"""

    product_id: int
    product_name: str
    standard_price: Decimal = Field(description="標準售價")
    tiers: List[VolumePricingTier] = Field(description="價格階層列表")


# ==========================================
# 促銷價 Schema
# ==========================================
class PromoPriceBase(BaseModel):
    """促銷價基礎 Schema"""

    promo_price: Decimal = Field(ge=0, description="促銷價格")
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    applicable_stores: Optional[str] = Field(
        default=None,
        max_length=500,
        description="適用門市（JSON 格式）",
    )

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v, info):
        """驗證結束日期必須在開始日期之後"""
        if v is not None:
            start = info.data.get("start_date")
            if start is not None and v <= start:
                raise ValueError("結束日期必須在開始日期之後")
        return v


class PromoPriceCreate(PromoPriceBase):
    """促銷價建立 Schema"""

    pass


class PromoPriceUpdate(BaseModel):
    """促銷價更新 Schema"""

    promo_price: Optional[Decimal] = Field(default=None, ge=0, description="促銷價格")
    start_date: Optional[datetime] = Field(default=None, description="開始日期")
    end_date: Optional[datetime] = Field(default=None, description="結束日期")
    applicable_stores: Optional[str] = Field(
        default=None,
        max_length=500,
        description="適用門市",
    )
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class PromoPriceResponse(PromoPriceBase):
    """促銷價回應 Schema"""

    id: int
    product_id: int
    is_active: bool
    is_valid: bool = Field(description="是否在有效期內")

    model_config = {"from_attributes": True}


# ==========================================
# 批次操作 Schema
# ==========================================
class BulkVolumePricingCreate(BaseModel):
    """批次建立量販價項目"""

    product_id: int = Field(description="商品 ID")
    tiers: List[VolumePricingCreate] = Field(min_length=1, description="價格階層列表")


class BulkVolumePricingRequest(BaseModel):
    """批次建立量販價請求"""

    items: List[BulkVolumePricingCreate] = Field(min_length=1, description="商品列表")


# ==========================================
# 價格計算 Schema
# ==========================================
class CalculatePriceRequest(BaseModel):
    """計算價格請求 Schema"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(ge=1, description="購買數量")
    customer_level_id: Optional[int] = Field(default=None, description="客戶等級 ID")
    store_id: Optional[int] = Field(default=None, description="門市 ID")


class CalculatePriceResponse(BaseModel):
    """計算價格回應 Schema"""

    product_id: int
    quantity: int
    standard_unit_price: Decimal = Field(description="標準單價")
    applied_unit_price: Decimal = Field(description="適用單價")
    price_type: str = Field(description="價格類型（標準/量販/促銷/會員）")
    total_amount: Decimal = Field(description="總金額")
    discount_amount: Decimal = Field(description="折扣金額")
    discount_percentage: Decimal = Field(description="折扣百分比")
