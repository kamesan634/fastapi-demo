"""
供應商相關 Schema 模型

定義供應商的請求和回應模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SupplierBase(BaseModel):
    """供應商基礎模型"""

    code: str = Field(max_length=20, description="供應商代碼")
    name: str = Field(max_length=100, description="供應商名稱")
    contact_name: Optional[str] = Field(default=None, max_length=50, description="聯絡人姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    email: Optional[EmailStr] = Field(default=None, description="電子郵件")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    tax_id: Optional[str] = Field(default=None, max_length=20, description="統一編號")
    payment_terms: int = Field(default=30, ge=0, description="付款條件（天數）")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    is_active: bool = Field(default=True, description="是否啟用")


class SupplierCreate(SupplierBase):
    """供應商建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "SUP001",
                    "name": "可口可樂公司",
                    "contact_name": "李經理",
                    "phone": "02-87654321",
                    "email": "supplier@cocacola.com",
                    "address": "台北市內湖區某某路200號",
                    "tax_id": "12345678",
                    "payment_terms": 30,
                    "notes": "主要飲料供應商",
                    "is_active": True,
                }
            ]
        }
    }


class SupplierUpdate(BaseModel):
    """供應商更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="供應商代碼")
    name: Optional[str] = Field(default=None, max_length=100, description="供應商名稱")
    contact_name: Optional[str] = Field(default=None, max_length=50, description="聯絡人姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    email: Optional[EmailStr] = Field(default=None, description="電子郵件")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    tax_id: Optional[str] = Field(default=None, max_length=20, description="統一編號")
    payment_terms: Optional[int] = Field(default=None, ge=0, description="付款條件（天數）")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class SupplierResponse(SupplierBase):
    """供應商回應模型"""

    id: int = Field(description="供應商 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}
