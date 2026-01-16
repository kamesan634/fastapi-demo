"""
付款方式管理 Schema

定義付款方式的請求與回應模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaymentMethodSettingBase(BaseModel):
    """付款方式基礎 Schema"""

    code: str = Field(..., min_length=1, max_length=20, description="付款方式代碼")
    name: str = Field(..., min_length=1, max_length=50, description="付款方式名稱")
    requires_change: bool = Field(default=False, description="是否需要找零")
    requires_authorization: bool = Field(default=False, description="是否需要授權碼")
    icon: Optional[str] = Field(default=None, max_length=100, description="圖示")
    sort_order: int = Field(default=0, ge=0, description="排序")
    is_active: bool = Field(default=True, description="是否啟用")


class PaymentMethodSettingCreate(PaymentMethodSettingBase):
    """建立付款方式請求 Schema"""

    pass


class PaymentMethodSettingUpdate(BaseModel):
    """更新付款方式請求 Schema"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    requires_change: Optional[bool] = None
    requires_authorization: Optional[bool] = None
    icon: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class PaymentMethodSettingResponse(PaymentMethodSettingBase):
    """付款方式回應 Schema"""

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None

    class Config:
        from_attributes = True
