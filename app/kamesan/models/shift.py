"""
班次管理模型

定義收銀員班次的資料模型。

模型：
- CashierShift: 收銀員班次
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class ShiftStatus(str, Enum):
    """班次狀態"""

    OPEN = "OPEN"      # 開班中
    CLOSED = "CLOSED"  # 已關班


class CashierShift(TimestampMixin, AuditMixin, table=True):
    """
    收銀員班次模型

    欄位：
    - id: 主鍵
    - store_id: 門市 ID
    - pos_id: POS 機台編號
    - cashier_id: 收銀員 ID
    - shift_date: 班次日期
    - start_time: 開班時間
    - end_time: 關班時間
    - opening_cash: 開班現金
    - expected_cash: 預期現金（系統計算）
    - actual_cash: 實際清點現金
    - cash_difference: 現金差異
    - difference_note: 差異說明
    - total_sales: 總銷售額
    - total_refunds: 總退款金額
    - total_transactions: 總交易筆數
    - total_cash_sales: 現金銷售額
    - total_card_sales: 刷卡銷售額
    - total_other_sales: 其他方式銷售額
    - status: 班次狀態
    - approved_by: 主管核准人 ID
    - notes: 備註
    """

    __tablename__ = "cashier_shifts"

    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: int = Field(
        foreign_key="stores.id",
        index=True,
        description="門市 ID",
    )
    pos_id: Optional[str] = Field(
        default=None,
        max_length=20,
        description="POS 機台編號",
    )
    cashier_id: int = Field(
        foreign_key="users.id",
        index=True,
        description="收銀員 ID",
    )
    shift_date: date = Field(
        index=True,
        description="班次日期",
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="開班時間",
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="關班時間",
    )

    # 現金相關
    opening_cash: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="開班現金",
    )
    expected_cash: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="預期現金",
    )
    actual_cash: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="實際清點現金",
    )
    cash_difference: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="現金差異",
    )
    difference_note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="差異說明",
    )

    # 銷售統計
    total_sales: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總銷售額",
    )
    total_refunds: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總退款金額",
    )
    total_transactions: int = Field(
        default=0,
        description="總交易筆數",
    )
    total_cash_sales: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="現金銷售額",
    )
    total_card_sales: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="刷卡銷售額",
    )
    total_other_sales: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="其他方式銷售額",
    )

    # 狀態
    status: ShiftStatus = Field(
        default=ShiftStatus.OPEN,
        index=True,
        description="班次狀態",
    )
    approved_by: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        description="主管核准人 ID",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="備註",
    )
