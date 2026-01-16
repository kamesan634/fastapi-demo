"""
促銷與優惠券相關 Schema 模型

定義促銷和優惠券的請求和回應模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.kamesan.models.promotion import DiscountType, PromotionType


# ==========================================
# 促銷模型
# ==========================================
class PromotionBase(BaseModel):
    """促銷基礎模型"""

    code: str = Field(max_length=20, description="促銷代碼")
    name: str = Field(max_length=100, description="促銷名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="促銷描述")
    promotion_type: PromotionType = Field(description="促銷類型")
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=0, description="折扣值")
    min_purchase: Decimal = Field(default=Decimal("0.00"), ge=0, description="最低消費金額")
    max_discount: Optional[Decimal] = Field(default=None, ge=0, description="最高折扣金額")
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    is_active: bool = Field(default=True, description="是否啟用")
    usage_limit: Optional[int] = Field(default=None, ge=0, description="使用次數上限")


class PromotionCreate(PromotionBase):
    """促銷建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "SUMMER2024",
                    "name": "夏季特賣",
                    "description": "夏季限定優惠，全館9折",
                    "promotion_type": "PERCENTAGE",
                    "discount_value": "10.00",
                    "min_purchase": "500.00",
                    "max_discount": "200.00",
                    "start_date": "2024-06-01T00:00:00",
                    "end_date": "2024-08-31T23:59:59",
                    "is_active": True,
                    "usage_limit": 1000,
                }
            ]
        }
    }


class PromotionUpdate(BaseModel):
    """促銷更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="促銷代碼")
    name: Optional[str] = Field(default=None, max_length=100, description="促銷名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="促銷描述")
    promotion_type: Optional[PromotionType] = Field(default=None, description="促銷類型")
    discount_value: Optional[Decimal] = Field(default=None, ge=0, description="折扣值")
    min_purchase: Optional[Decimal] = Field(default=None, ge=0, description="最低消費金額")
    max_discount: Optional[Decimal] = Field(default=None, ge=0, description="最高折扣金額")
    start_date: Optional[datetime] = Field(default=None, description="開始日期")
    end_date: Optional[datetime] = Field(default=None, description="結束日期")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
    usage_limit: Optional[int] = Field(default=None, ge=0, description="使用次數上限")


class PromotionResponse(PromotionBase):
    """促銷回應模型"""

    id: int = Field(description="促銷 ID")
    used_count: int = Field(description="已使用次數")
    is_valid: bool = Field(description="是否有效")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 優惠券模型
# ==========================================
class CouponBase(BaseModel):
    """優惠券基礎模型"""

    code: str = Field(max_length=30, description="優惠券代碼")
    name: str = Field(max_length=100, description="優惠券名稱")
    discount_type: DiscountType = Field(description="折扣類型")
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=0, description="折扣值")
    min_purchase: Decimal = Field(default=Decimal("0.00"), ge=0, description="最低消費金額")
    max_discount: Optional[Decimal] = Field(default=None, ge=0, description="最高折扣金額")
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    is_active: bool = Field(default=True, description="是否啟用")
    customer_id: Optional[int] = Field(default=None, description="客戶 ID（綁定特定客戶）")


class CouponCreate(CouponBase):
    """優惠券建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "WELCOME100",
                    "name": "新會員折價券",
                    "discount_type": "FIXED_AMOUNT",
                    "discount_value": "100.00",
                    "min_purchase": "500.00",
                    "max_discount": None,
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-12-31T23:59:59",
                    "is_active": True,
                    "customer_id": 1,
                }
            ]
        }
    }


class CouponUpdate(BaseModel):
    """優惠券更新模型"""

    code: Optional[str] = Field(default=None, max_length=30, description="優惠券代碼")
    name: Optional[str] = Field(default=None, max_length=100, description="優惠券名稱")
    discount_type: Optional[DiscountType] = Field(default=None, description="折扣類型")
    discount_value: Optional[Decimal] = Field(default=None, ge=0, description="折扣值")
    min_purchase: Optional[Decimal] = Field(default=None, ge=0, description="最低消費金額")
    max_discount: Optional[Decimal] = Field(default=None, ge=0, description="最高折扣金額")
    start_date: Optional[datetime] = Field(default=None, description="開始日期")
    end_date: Optional[datetime] = Field(default=None, description="結束日期")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
    customer_id: Optional[int] = Field(default=None, description="客戶 ID")


class CouponResponse(CouponBase):
    """優惠券回應模型"""

    id: int = Field(description="優惠券 ID")
    is_used: bool = Field(description="是否已使用")
    used_at: Optional[datetime] = Field(description="使用時間")
    order_id: Optional[int] = Field(description="訂單 ID")
    is_valid: bool = Field(description="是否有效")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}
