"""
客戶與客戶等級模型

定義客戶與客戶等級的資料模型。

模型：
- CustomerLevel: 客戶等級（定義不同等級的折扣）
- Customer: 客戶（會員資料）
- PointsLog: 點數異動記錄
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.order import Order


class PointsLogType(str, Enum):
    """點數異動類型"""

    EARN = "EARN"  # 消費獲得
    REDEEM = "REDEEM"  # 點數折抵
    BONUS = "BONUS"  # 活動贈點
    ADJUST = "ADJUST"  # 手動調整
    EXPIRE = "EXPIRE"  # 點數過期
    REFUND = "REFUND"  # 退貨扣點
    TRANSFER = "TRANSFER"  # 點數轉移


class CustomerLevel(TimestampMixin, table=True):
    """
    客戶等級模型

    定義不同的客戶等級與對應的折扣。

    欄位：
    - id: 主鍵
    - code: 等級代碼（唯一）
    - name: 等級名稱
    - discount_rate: 折扣率（0.00 ~ 1.00）
    - min_spending: 升級所需最低消費金額
    - description: 等級描述
    - is_active: 是否啟用

    關聯：
    - customers: 此等級的所有客戶
    """

    __tablename__ = "customer_levels"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="等級代碼",
    )
    name: str = Field(max_length=50, description="等級名稱")
    discount_rate: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=3,
        decimal_places=2,
        description="折扣率",
    )
    min_spending: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="升級最低消費",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="等級描述",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    customers: List["Customer"] = Relationship(back_populates="level")

    def __repr__(self) -> str:
        return f"<CustomerLevel {self.code}: {self.name}>"


class Customer(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    客戶模型

    會員資料，包含基本資訊與消費統計。

    欄位：
    - id: 主鍵
    - code: 會員編號（唯一）
    - name: 姓名
    - phone: 電話
    - email: 電子郵件
    - birthday: 生日
    - address: 地址
    - total_spending: 累計消費金額
    - points: 累計點數
    - level_id: 客戶等級 ID
    - is_active: 是否啟用

    關聯：
    - level: 客戶等級
    - orders: 客戶的訂單列表
    """

    __tablename__ = "customers"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="會員編號",
    )
    name: str = Field(max_length=50, description="姓名")
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        index=True,
        description="電話",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=100,
        description="電子郵件",
    )
    birthday: Optional[date] = Field(default=None, description="生日")
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="地址",
    )
    total_spending: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="累計消費金額",
    )
    points: int = Field(default=0, description="累計點數")
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    level_id: Optional[int] = Field(
        default=None,
        foreign_key="customer_levels.id",
        description="客戶等級 ID",
    )

    # 關聯
    level: Optional[CustomerLevel] = Relationship(back_populates="customers")
    orders: List["Order"] = Relationship(back_populates="customer")
    points_logs: List["PointsLog"] = Relationship(back_populates="customer")

    def add_spending(self, amount: Decimal) -> None:
        """增加消費金額"""
        self.total_spending += amount

    def add_points(self, points: int) -> None:
        """增加點數"""
        self.points += points

    def use_points(self, points: int) -> bool:
        """使用點數"""
        if self.points >= points:
            self.points -= points
            return True
        return False

    def __repr__(self) -> str:
        return f"<Customer {self.code}: {self.name}>"


class PointsLog(TimestampMixin, AuditMixin, table=True):
    """
    點數異動記錄模型

    記錄客戶點數的所有異動。

    欄位：
    - id: 主鍵
    - customer_id: 客戶 ID
    - type: 異動類型
    - points: 異動點數（正數增加，負數減少）
    - balance: 異動後餘額
    - reference_type: 參考單據類型（如 Order）
    - reference_id: 參考單據 ID
    - description: 異動說明
    - expire_date: 點數到期日

    關聯：
    - customer: 客戶
    """

    __tablename__ = "points_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    type: PointsLogType = Field(description="異動類型")
    points: int = Field(description="異動點數")
    balance: int = Field(description="異動後餘額")
    reference_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="參考單據類型",
    )
    reference_id: Optional[int] = Field(
        default=None,
        description="參考單據 ID",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="異動說明",
    )
    expire_date: Optional[date] = Field(
        default=None,
        description="點數到期日",
    )

    # 外鍵
    customer_id: int = Field(
        foreign_key="customers.id",
        index=True,
        description="客戶 ID",
    )

    # 關聯
    customer: Optional["Customer"] = Relationship(back_populates="points_logs")

    def __repr__(self) -> str:
        return f"<PointsLog {self.type} {self.points}>"
