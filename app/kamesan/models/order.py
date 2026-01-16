"""
訂單相關模型

定義訂單、訂單明細、付款等資料模型。

模型：
- Order: 訂單主檔
- OrderItem: 訂單明細
- Payment: 付款記錄
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.customer import Customer
    from app.kamesan.models.product import Product
    from app.kamesan.models.store import Store


class OrderStatus(str, Enum):
    """訂單狀態"""

    PENDING = "PENDING"  # 待處理
    CONFIRMED = "CONFIRMED"  # 已確認
    PROCESSING = "PROCESSING"  # 處理中
    COMPLETED = "COMPLETED"  # 已完成
    CANCELLED = "CANCELLED"  # 已取消
    REFUNDED = "REFUNDED"  # 已退款


class PaymentMethod(str, Enum):
    """付款方式"""

    CASH = "CASH"  # 現金
    CREDIT_CARD = "CREDIT_CARD"  # 信用卡
    DEBIT_CARD = "DEBIT_CARD"  # 金融卡
    LINE_PAY = "LINE_PAY"  # LINE Pay
    APPLE_PAY = "APPLE_PAY"  # Apple Pay
    POINTS = "POINTS"  # 點數折抵


class PaymentStatus(str, Enum):
    """付款狀態"""

    PENDING = "PENDING"  # 待付款
    PAID = "PAID"  # 已付款
    FAILED = "FAILED"  # 付款失敗
    REFUNDED = "REFUNDED"  # 已退款


class SalesReturnStatus(str, Enum):
    """銷售退貨狀態"""

    PENDING = "PENDING"  # 待處理
    APPROVED = "APPROVED"  # 已核准
    COMPLETED = "COMPLETED"  # 已完成
    REJECTED = "REJECTED"  # 已拒絕


class ReturnReason(str, Enum):
    """退貨原因"""

    DEFECTIVE = "DEFECTIVE"  # 瑕疵品
    WRONG_ITEM = "WRONG_ITEM"  # 商品錯誤
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"  # 與描述不符
    CHANGE_OF_MIND = "CHANGE_OF_MIND"  # 改變心意
    OTHER = "OTHER"  # 其他


class PaymentMethodSetting(TimestampMixin, AuditMixin, table=True):
    """
    付款方式設定模型

    可動態管理付款方式，支援新增、編輯、停用。

    欄位：
    - id: 主鍵
    - code: 付款方式代碼（唯一）
    - name: 付款方式名稱
    - requires_change: 是否需要找零（現金類）
    - requires_authorization: 是否需要授權碼（信用卡類）
    - icon: 圖示 class 或 URL
    - sort_order: 排序
    - is_active: 是否啟用
    """

    __tablename__ = "payment_method_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="付款方式代碼",
    )
    name: str = Field(max_length=50, description="付款方式名稱")
    requires_change: bool = Field(default=False, description="是否需要找零")
    requires_authorization: bool = Field(default=False, description="是否需要授權碼")
    icon: Optional[str] = Field(
        default=None,
        max_length=100,
        description="圖示",
    )
    sort_order: int = Field(default=0, description="排序")
    is_active: bool = Field(default=True, description="是否啟用")

    def __repr__(self) -> str:
        return f"<PaymentMethodSetting {self.code}>"


class Order(TimestampMixin, AuditMixin, table=True):
    """
    訂單模型

    記錄銷售訂單的主要資訊。

    欄位：
    - id: 主鍵
    - order_number: 訂單編號（唯一）
    - store_id: 門市 ID
    - customer_id: 客戶 ID
    - status: 訂單狀態
    - subtotal: 小計（未稅）
    - tax_amount: 稅額
    - discount_amount: 折扣金額
    - total_amount: 總金額
    - points_earned: 獲得點數
    - points_used: 使用點數
    - notes: 備註
    - order_date: 訂單日期

    關聯：
    - store: 門市
    - customer: 客戶
    - items: 訂單明細列表
    - payments: 付款記錄列表
    """

    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="訂單編號",
    )
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        description="訂單狀態",
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="小計（未稅）",
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="稅額",
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="折扣金額",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總金額",
    )
    points_earned: int = Field(default=0, description="獲得點數")
    points_used: int = Field(default=0, description="使用點數")
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    order_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="訂單日期",
    )

    # 外鍵
    store_id: Optional[int] = Field(
        default=None,
        foreign_key="stores.id",
        description="門市 ID",
    )
    customer_id: Optional[int] = Field(
        default=None,
        foreign_key="customers.id",
        description="客戶 ID",
    )

    # 關聯
    store: Optional["Store"] = Relationship(back_populates="orders")
    customer: Optional["Customer"] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    payments: List["Payment"] = Relationship(back_populates="order")
    sales_returns: List["SalesReturn"] = Relationship(back_populates="order")

    def calculate_totals(self) -> None:
        """計算訂單金額"""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.tax_amount = sum(item.tax_amount for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

    def cancel(self) -> None:
        """取消訂單"""
        self.status = OrderStatus.CANCELLED

    def complete(self) -> None:
        """完成訂單"""
        self.status = OrderStatus.COMPLETED

    def __repr__(self) -> str:
        return f"<Order {self.order_number}>"


class OrderItem(TimestampMixin, table=True):
    """
    訂單明細模型

    記錄訂單中每個商品的詳細資訊。

    欄位：
    - id: 主鍵
    - order_id: 訂單 ID
    - product_id: 商品 ID
    - product_name: 商品名稱（快照）
    - quantity: 數量
    - unit_price: 單價
    - discount_amount: 折扣金額
    - subtotal: 小計
    - tax_rate: 稅率
    - tax_amount: 稅額

    關聯：
    - order: 訂單
    - product: 商品
    """

    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str = Field(max_length=100, description="商品名稱（快照）")
    quantity: int = Field(default=1, description="數量")
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="折扣金額",
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="小計",
    )
    tax_rate: Decimal = Field(
        default=Decimal("0.05"),
        max_digits=5,
        decimal_places=4,
        description="稅率",
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="稅額",
    )

    # 外鍵
    order_id: int = Field(
        foreign_key="orders.id",
        description="訂單 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    order: Optional["Order"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="order_items")

    def calculate(self) -> None:
        """計算明細金額"""
        self.subtotal = self.unit_price * self.quantity - self.discount_amount
        self.tax_amount = self.subtotal * self.tax_rate

    def __repr__(self) -> str:
        return f"<OrderItem {self.product_name} x{self.quantity}>"


class Payment(TimestampMixin, table=True):
    """
    付款記錄模型

    記錄訂單的付款資訊。

    欄位：
    - id: 主鍵
    - order_id: 訂單 ID
    - payment_method: 付款方式
    - amount: 付款金額
    - status: 付款狀態
    - transaction_id: 交易編號（第三方支付）
    - paid_at: 付款時間

    關聯：
    - order: 訂單
    """

    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    payment_method: PaymentMethod = Field(description="付款方式")
    amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="付款金額",
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="付款狀態",
    )
    transaction_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="交易編號",
    )
    paid_at: Optional[datetime] = Field(
        default=None,
        description="付款時間",
    )

    # 外鍵
    order_id: int = Field(
        foreign_key="orders.id",
        description="訂單 ID",
    )

    # 關聯
    order: Optional["Order"] = Relationship(back_populates="payments")

    def mark_paid(self, transaction_id: Optional[str] = None) -> None:
        """標記為已付款"""
        self.status = PaymentStatus.PAID
        self.paid_at = datetime.now(timezone.utc)
        if transaction_id:
            self.transaction_id = transaction_id

    def mark_failed(self) -> None:
        """標記為付款失敗"""
        self.status = PaymentStatus.FAILED

    def refund(self) -> None:
        """退款"""
        self.status = PaymentStatus.REFUNDED

    def __repr__(self) -> str:
        return f"<Payment {self.payment_method} {self.amount}>"


class SalesReturn(TimestampMixin, AuditMixin, table=True):
    """
    銷售退貨模型

    記錄銷售退貨單的主要資訊。

    欄位：
    - id: 主鍵
    - return_number: 退貨單號（唯一）
    - order_id: 原訂單 ID
    - store_id: 門市 ID
    - customer_id: 客戶 ID
    - status: 退貨狀態
    - reason: 退貨原因
    - reason_detail: 退貨原因說明
    - total_amount: 退款金額
    - points_deducted: 扣除點數
    - notes: 備註

    關聯：
    - order: 原訂單
    - items: 退貨明細列表
    """

    __tablename__ = "sales_returns"

    id: Optional[int] = Field(default=None, primary_key=True)
    return_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="退貨單號",
    )
    status: SalesReturnStatus = Field(
        default=SalesReturnStatus.PENDING,
        description="退貨狀態",
    )
    reason: ReturnReason = Field(description="退貨原因")
    reason_detail: Optional[str] = Field(
        default=None,
        max_length=500,
        description="退貨原因說明",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="退款金額",
    )
    points_deducted: int = Field(default=0, description="扣除點數")
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    return_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="退貨日期",
    )

    # 外鍵
    order_id: int = Field(
        foreign_key="orders.id",
        description="原訂單 ID",
    )
    store_id: Optional[int] = Field(
        default=None,
        foreign_key="stores.id",
        description="門市 ID",
    )
    customer_id: Optional[int] = Field(
        default=None,
        foreign_key="customers.id",
        description="客戶 ID",
    )

    # 關聯
    order: Optional["Order"] = Relationship(back_populates="sales_returns")
    items: List["SalesReturnItem"] = Relationship(back_populates="sales_return")

    def approve(self) -> None:
        """核准退貨"""
        self.status = SalesReturnStatus.APPROVED

    def complete(self) -> None:
        """完成退貨"""
        self.status = SalesReturnStatus.COMPLETED

    def reject(self) -> None:
        """拒絕退貨"""
        self.status = SalesReturnStatus.REJECTED

    def __repr__(self) -> str:
        return f"<SalesReturn {self.return_number}>"


class SalesReturnItem(TimestampMixin, table=True):
    """
    銷售退貨明細模型

    記錄退貨單中每個商品的詳細資訊。

    欄位：
    - id: 主鍵
    - sales_return_id: 退貨單 ID
    - order_item_id: 原訂單明細 ID
    - product_id: 商品 ID
    - product_name: 商品名稱
    - quantity: 退貨數量
    - unit_price: 單價
    - subtotal: 小計

    關聯：
    - sales_return: 退貨單
    - product: 商品
    """

    __tablename__ = "sales_return_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str = Field(max_length=100, description="商品名稱（快照）")
    quantity: int = Field(default=1, description="退貨數量")
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="小計",
    )

    # 外鍵
    sales_return_id: int = Field(
        foreign_key="sales_returns.id",
        description="退貨單 ID",
    )
    order_item_id: Optional[int] = Field(
        default=None,
        foreign_key="order_items.id",
        description="原訂單明細 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    sales_return: Optional["SalesReturn"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="sales_return_items")

    def __repr__(self) -> str:
        return f"<SalesReturnItem {self.product_name} x{self.quantity}>"
