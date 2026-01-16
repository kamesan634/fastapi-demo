"""
系統設定模型

定義系統設定相關的資料模型。

模型：
- NumberingRule: 編號規則設定
- NumberingSequence: 編號流水號
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class DocumentType(str, Enum):
    """單據類型"""

    SALES_ORDER = "SALES_ORDER"  # 銷售單
    PURCHASE_ORDER = "PURCHASE_ORDER"  # 採購單
    GOODS_RECEIPT = "GOODS_RECEIPT"  # 進貨單
    SALES_RETURN = "SALES_RETURN"  # 退貨單
    PURCHASE_RETURN = "PURCHASE_RETURN"  # 採購退貨單
    STOCK_COUNT = "STOCK_COUNT"  # 盤點單
    STOCK_TRANSFER = "STOCK_TRANSFER"  # 調撥單


class DateFormat(str, Enum):
    """日期格式"""

    YYYYMMDD = "YYYYMMDD"  # 年月日
    YYYYMM = "YYYYMM"  # 年月
    YYYY = "YYYY"  # 年
    NONE = "NONE"  # 無日期


class ResetPeriod(str, Enum):
    """重置週期"""

    DAILY = "DAILY"  # 每日
    MONTHLY = "MONTHLY"  # 每月
    YEARLY = "YEARLY"  # 每年
    NEVER = "NEVER"  # 不重置


class NumberingRule(TimestampMixin, AuditMixin, table=True):
    """
    編號規則設定模型

    定義各類單據的自動編號規則。

    欄位：
    - id: 主鍵
    - document_type: 單據類型（唯一）
    - prefix: 前綴
    - date_format: 日期格式
    - sequence_digits: 流水號位數
    - reset_period: 重置週期
    - is_active: 是否啟用
    """

    __tablename__ = "numbering_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_type: DocumentType = Field(
        unique=True,
        index=True,
        description="單據類型",
    )
    prefix: str = Field(max_length=10, description="前綴")
    date_format: DateFormat = Field(
        default=DateFormat.YYYYMMDD,
        description="日期格式",
    )
    sequence_digits: int = Field(
        default=4,
        ge=3,
        le=10,
        description="流水號位數",
    )
    reset_period: ResetPeriod = Field(
        default=ResetPeriod.DAILY,
        description="重置週期",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    def __repr__(self) -> str:
        return f"<NumberingRule {self.document_type}: {self.prefix}>"


class NumberingSequence(TimestampMixin, table=True):
    """
    編號流水號模型

    記錄各單據類型的當前流水號。

    欄位：
    - id: 主鍵
    - document_type: 單據類型
    - period_key: 週期鍵值（如 20251231、202512、2025）
    - current_sequence: 當前流水號
    """

    __tablename__ = "numbering_sequences"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_type: DocumentType = Field(
        index=True,
        description="單據類型",
    )
    period_key: str = Field(
        max_length=20,
        index=True,
        description="週期鍵值",
    )
    current_sequence: int = Field(
        default=0,
        description="當前流水號",
    )

    def __repr__(self) -> str:
        return f"<NumberingSequence {self.document_type} {self.period_key}: {self.current_sequence}>"
