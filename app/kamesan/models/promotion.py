"""
促銷與優惠券模型

定義促銷活動與優惠券的資料模型。

模型：
- Promotion: 促銷活動
- Coupon: 優惠券
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class PromotionType(str, Enum):
    """促銷類型"""

    PERCENTAGE = "PERCENTAGE"  # 百分比折扣
    FIXED_AMOUNT = "FIXED_AMOUNT"  # 固定金額折扣
    BUY_X_GET_Y = "BUY_X_GET_Y"  # 買X送Y
    BUNDLE = "BUNDLE"  # 組合優惠


class DiscountType(str, Enum):
    """折扣類型"""

    PERCENTAGE = "PERCENTAGE"  # 百分比折扣
    FIXED_AMOUNT = "FIXED_AMOUNT"  # 固定金額折扣


class Promotion(TimestampMixin, AuditMixin, table=True):
    """
    促銷活動模型

    定義促銷活動的規則與期限。

    欄位：
    - id: 主鍵
    - code: 促銷代碼（唯一）
    - name: 促銷名稱
    - description: 促銷描述
    - promotion_type: 促銷類型
    - discount_value: 折扣值
    - min_purchase: 最低消費金額
    - max_discount: 最高折扣金額
    - start_date: 開始日期
    - end_date: 結束日期
    - is_active: 是否啟用
    - usage_limit: 使用次數上限
    - used_count: 已使用次數
    """

    __tablename__ = "promotions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="促銷代碼",
    )
    name: str = Field(max_length=100, description="促銷名稱")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="促銷描述",
    )
    promotion_type: PromotionType = Field(description="促銷類型")
    discount_value: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="折扣值",
    )
    min_purchase: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="最低消費金額",
    )
    max_discount: Optional[Decimal] = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="最高折扣金額",
    )
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    is_active: bool = Field(default=True, description="是否啟用")
    usage_limit: Optional[int] = Field(
        default=None,
        description="使用次數上限",
    )
    used_count: int = Field(default=0, description="已使用次數")

    @property
    def is_valid(self) -> bool:
        """檢查促銷是否有效"""
        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False
        # 處理 timezone-naive datetime 比較
        start = self.start_date.replace(tzinfo=timezone.utc) if self.start_date.tzinfo is None else self.start_date
        end = self.end_date.replace(tzinfo=timezone.utc) if self.end_date.tzinfo is None else self.end_date
        if now < start or now > end:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """計算折扣金額"""
        if amount < self.min_purchase:
            return Decimal("0.00")

        if self.promotion_type == PromotionType.PERCENTAGE:
            discount = amount * (self.discount_value / 100)
        elif self.promotion_type == PromotionType.FIXED_AMOUNT:
            discount = self.discount_value
        else:
            discount = Decimal("0.00")

        # 套用最高折扣限制
        if self.max_discount:
            discount = min(discount, self.max_discount)

        return discount

    def use(self) -> None:
        """使用促銷"""
        self.used_count += 1

    def __repr__(self) -> str:
        return f"<Promotion {self.code}: {self.name}>"


class Coupon(TimestampMixin, AuditMixin, table=True):
    """
    優惠券模型

    發放給客戶的優惠券。

    欄位：
    - id: 主鍵
    - code: 優惠券代碼（唯一）
    - name: 優惠券名稱
    - discount_type: 折扣類型
    - discount_value: 折扣值
    - min_purchase: 最低消費金額
    - max_discount: 最高折扣金額
    - start_date: 開始日期
    - end_date: 結束日期
    - is_active: 是否啟用
    - is_used: 是否已使用
    - used_at: 使用時間
    - customer_id: 客戶 ID（綁定特定客戶）
    - order_id: 使用此優惠券的訂單 ID
    """

    __tablename__ = "coupons"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="優惠券代碼",
    )
    name: str = Field(max_length=100, description="優惠券名稱")
    discount_type: DiscountType = Field(description="折扣類型")
    discount_value: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="折扣值",
    )
    min_purchase: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="最低消費金額",
    )
    max_discount: Optional[Decimal] = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="最高折扣金額",
    )
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    is_active: bool = Field(default=True, description="是否啟用")
    is_used: bool = Field(default=False, description="是否已使用")
    used_at: Optional[datetime] = Field(default=None, description="使用時間")

    # 外鍵
    customer_id: Optional[int] = Field(
        default=None,
        foreign_key="customers.id",
        description="客戶 ID",
    )
    order_id: Optional[int] = Field(
        default=None,
        foreign_key="orders.id",
        description="訂單 ID",
    )

    @property
    def is_valid(self) -> bool:
        """檢查優惠券是否有效"""
        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False
        if self.is_used:
            return False
        # 處理 timezone-naive datetime 比較
        start = self.start_date.replace(tzinfo=timezone.utc) if self.start_date.tzinfo is None else self.start_date
        end = self.end_date.replace(tzinfo=timezone.utc) if self.end_date.tzinfo is None else self.end_date
        if now < start or now > end:
            return False
        return True

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """計算折扣金額"""
        if amount < self.min_purchase:
            return Decimal("0.00")

        if self.discount_type == DiscountType.PERCENTAGE:
            discount = amount * (self.discount_value / 100)
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            discount = self.discount_value
        else:
            discount = Decimal("0.00")

        # 套用最高折扣限制
        if self.max_discount:
            discount = min(discount, self.max_discount)

        return discount

    def use(self, order_id: int) -> None:
        """使用優惠券"""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)
        self.order_id = order_id

    def __repr__(self) -> str:
        return f"<Coupon {self.code}: {self.name}>"
