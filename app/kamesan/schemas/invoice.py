"""
發票管理 Schema 模型

定義發票的請求和回應模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.kamesan.models.invoice import CarrierType, InvoiceType


# ==========================================
# 發票模型
# ==========================================
class InvoiceBase(BaseModel):
    """發票基礎模型"""

    order_id: int = Field(description="訂單 ID")
    invoice_type: InvoiceType = Field(default=InvoiceType.B2C, description="發票類型")


class InvoiceCreate(InvoiceBase):
    """發票建立模型"""

    # B2B 資訊
    buyer_tax_id: Optional[str] = Field(
        default=None, max_length=8, description="買方統編"
    )
    buyer_name: Optional[str] = Field(
        default=None, max_length=100, description="買方名稱"
    )

    # 載具資訊
    carrier_type: Optional[CarrierType] = Field(default=None, description="載具類型")
    carrier_no: Optional[str] = Field(
        default=None, max_length=64, description="載具號碼"
    )

    # 捐贈資訊
    donate_code: Optional[str] = Field(default=None, max_length=10, description="捐贈碼")

    # 是否列印
    print_flag: bool = Field(default=False, description="是否列印紙本")

    @field_validator("buyer_tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 8:
            raise ValueError("統一編號必須為 8 碼")
        if v and not v.isdigit():
            raise ValueError("統一編號必須為數字")
        return v

    @field_validator("carrier_no")
    @classmethod
    def validate_carrier_no(cls, v: Optional[str], info) -> Optional[str]:
        if not v:
            return v
        carrier_type = info.data.get("carrier_type")
        if carrier_type == CarrierType.MOBILE:
            # 手機條碼：/ 開頭，共 8 碼
            if not v.startswith("/") or len(v) != 8:
                raise ValueError("手機條碼格式錯誤（應為 / 開頭，共 8 碼）")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "order_id": 1,
                    "invoice_type": "B2C",
                    "print_flag": True,
                },
                {
                    "order_id": 2,
                    "invoice_type": "B2C_CARRIER",
                    "carrier_type": "MOBILE",
                    "carrier_no": "/ABC1234",
                    "print_flag": False,
                },
                {
                    "order_id": 3,
                    "invoice_type": "B2B",
                    "buyer_tax_id": "12345678",
                    "buyer_name": "測試公司",
                    "print_flag": True,
                },
            ]
        }
    }


class InvoiceVoidRequest(BaseModel):
    """發票作廢請求模型"""

    reason: str = Field(max_length=200, description="作廢原因")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reason": "客戶取消訂單",
                }
            ]
        }
    }


class InvoiceResponse(InvoiceBase):
    """發票回應模型"""

    id: int = Field(description="發票 ID")
    invoice_no: str = Field(description="發票號碼")
    invoice_date: datetime = Field(description="發票日期")

    # 買方資訊
    buyer_tax_id: Optional[str] = Field(default=None, description="買方統編")
    buyer_name: Optional[str] = Field(default=None, description="買方名稱")

    # 載具資訊
    carrier_type: Optional[CarrierType] = Field(default=None, description="載具類型")
    carrier_no: Optional[str] = Field(default=None, description="載具號碼")

    # 捐贈資訊
    donate_code: Optional[str] = Field(default=None, description="捐贈碼")

    # 金額
    sales_amount: Decimal = Field(description="銷售額（未稅）")
    tax_amount: Decimal = Field(description="稅額")
    total_amount: Decimal = Field(description="總金額")

    # 狀態
    print_flag: bool = Field(description="是否已列印")
    void_flag: bool = Field(description="是否作廢")
    void_date: Optional[datetime] = Field(default=None, description="作廢日期")
    void_reason: Optional[str] = Field(default=None, description="作廢原因")

    random_number: Optional[str] = Field(default=None, description="隨機碼")

    # 時間戳
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    created_by: Optional[int] = Field(default=None, description="建立者 ID")
    updated_by: Optional[int] = Field(default=None, description="更新者 ID")

    model_config = {"from_attributes": True}


class InvoiceSummary(BaseModel):
    """發票摘要（用於列表顯示）"""

    id: int = Field(description="發票 ID")
    invoice_no: str = Field(description="發票號碼")
    order_id: int = Field(description="訂單 ID")
    invoice_date: datetime = Field(description="發票日期")
    invoice_type: InvoiceType = Field(description="發票類型")
    total_amount: Decimal = Field(description="總金額")
    void_flag: bool = Field(description="是否作廢")

    model_config = {"from_attributes": True}
