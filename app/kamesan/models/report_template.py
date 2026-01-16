"""
報表範本模型

定義自訂報表範本的資料模型。

模型：
- ReportTemplate: 報表範本
"""

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin


class ReportType(str, Enum):
    """報表類型"""

    SALES_DAILY = "SALES_DAILY"           # 每日銷售報表
    SALES_SUMMARY = "SALES_SUMMARY"       # 銷售彙總報表
    INVENTORY = "INVENTORY"               # 庫存報表
    INVENTORY_MOVEMENT = "INVENTORY_MOVEMENT"  # 庫存異動報表
    PROFIT_ANALYSIS = "PROFIT_ANALYSIS"   # 利潤分析報表
    CUSTOMER = "CUSTOMER"                 # 客戶分析報表
    TOP_PRODUCTS = "TOP_PRODUCTS"         # 熱銷商品報表
    PURCHASE = "PURCHASE"                 # 採購報表
    CUSTOM = "CUSTOM"                     # 自訂報表


class ReportTemplate(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    報表範本模型

    欄位：
    - id: 主鍵
    - code: 報表代碼（唯一）
    - name: 報表名稱
    - description: 說明
    - report_type: 報表類型
    - fields_config: 欄位設定 (JSON)
    - filters_config: 篩選設定 (JSON)
    - sort_config: 排序設定 (JSON)
    - format_config: 格式設定 (JSON)
    - is_public: 是否公開
    - owner_id: 擁有者 ID
    - is_system: 是否系統內建
    - is_active: 是否啟用
    """

    __tablename__ = "report_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=50,
        unique=True,
        index=True,
        description="報表代碼",
    )
    name: str = Field(max_length=100, description="報表名稱")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="說明",
    )
    report_type: ReportType = Field(
        default=ReportType.CUSTOM,
        index=True,
        description="報表類型",
    )

    # JSON 設定
    fields_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="欄位設定",
    )
    filters_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="篩選設定",
    )
    sort_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="排序設定",
    )
    format_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="格式設定",
    )

    # 權限
    is_public: bool = Field(default=False, description="是否公開")
    owner_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
        description="擁有者 ID",
    )
    is_system: bool = Field(default=False, description="是否系統內建")
    is_active: bool = Field(default=True, description="是否啟用")
