"""
發票管理模型

定義電子發票的資料模型。

模型：
- Invoice: 電子發票
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class InvoiceType(str, Enum):
    """發票類型"""

    B2C = "B2C"                    # 一般消費者（二聯式）
    B2C_CARRIER = "B2C_CARRIER"   # 載具發票
    B2C_DONATE = "B2C_DONATE"     # 捐贈發票
    B2B = "B2B"                    # 營業人（三聯式）


class CarrierType(str, Enum):
    """載具類型"""

    MOBILE = "MOBILE"          # 手機條碼
    NATURAL = "NATURAL"        # 自然人憑證
    MEMBER = "MEMBER"          # 會員載具


class Invoice(TimestampMixin, AuditMixin, table=True):
    """
    電子發票模型

    欄位：
    - id: 主鍵
    - invoice_no: 發票號碼
    - order_id: 訂單 ID
    - invoice_date: 發票日期
    - invoice_type: 發票類型
    - buyer_tax_id: 買方統編（B2B 必填）
    - buyer_name: 買方名稱（B2B 必填）
    - carrier_type: 載具類型
    - carrier_no: 載具號碼
    - donate_code: 捐贈碼（愛心碼）
    - sales_amount: 銷售額（未稅）
    - tax_amount: 稅額
    - total_amount: 總金額
    - print_flag: 是否已列印
    - void_flag: 是否作廢
    - void_date: 作廢日期
    - void_reason: 作廢原因
    - random_number: 隨機碼
    """

    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_no: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="發票號碼",
    )
    order_id: int = Field(
        foreign_key="orders.id",
        index=True,
        description="訂單 ID",
    )
    invoice_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="發票日期",
    )
    invoice_type: InvoiceType = Field(
        default=InvoiceType.B2C,
        index=True,
        description="發票類型",
    )

    # 買方資訊（B2B）
    buyer_tax_id: Optional[str] = Field(
        default=None,
        max_length=8,
        description="買方統編",
    )
    buyer_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="買方名稱",
    )

    # 載具資訊
    carrier_type: Optional[CarrierType] = Field(
        default=None,
        description="載具類型",
    )
    carrier_no: Optional[str] = Field(
        default=None,
        max_length=64,
        description="載具號碼",
    )

    # 捐贈資訊
    donate_code: Optional[str] = Field(
        default=None,
        max_length=10,
        description="捐贈碼",
    )

    # 金額
    sales_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="銷售額（未稅）",
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="稅額",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總金額",
    )

    # 狀態
    print_flag: bool = Field(default=False, description="是否已列印")
    void_flag: bool = Field(default=False, index=True, description="是否作廢")
    void_date: Optional[datetime] = Field(
        default=None,
        description="作廢日期",
    )
    void_reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="作廢原因",
    )

    # 其他
    random_number: Optional[str] = Field(
        default=None,
        max_length=4,
        description="隨機碼",
    )
