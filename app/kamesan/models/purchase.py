"""
採購相關模型

定義採購單、驗收單、退貨單、供應商價格等資料模型。

模型：
- PurchaseOrder: 採購單
- PurchaseOrderItem: 採購單明細
- PurchaseReceipt: 驗收單
- PurchaseReceiptItem: 驗收單明細
- PurchaseReturn: 退貨單
- PurchaseReturnItem: 退貨單明細
- SupplierPrice: 供應商商品報價
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product
    from app.kamesan.models.store import Warehouse
    from app.kamesan.models.supplier import Supplier


class PurchaseOrderStatus(str, Enum):
    """
    採購單狀態

    狀態說明：
    - DRAFT: 草稿（採購單建立但尚未提交）
    - PENDING: 待審核（採購單已提交，等待審核）
    - APPROVED: 已核准（採購單已核准，等待收貨）
    - PARTIAL: 部分收貨（部分商品已驗收）
    - COMPLETED: 已完成（全部商品已驗收）
    - CANCELLED: 已取消（採購單被取消）
    """

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PurchaseReceiptStatus(str, Enum):
    """
    驗收單狀態

    狀態說明：
    - PENDING: 待驗收
    - COMPLETED: 已完成
    - CANCELLED: 已取消
    """

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PurchaseReturnStatus(str, Enum):
    """
    退貨單狀態

    狀態說明：
    - DRAFT: 草稿
    - PENDING: 待審核
    - APPROVED: 已核准
    - COMPLETED: 已完成（退貨已退回供應商）
    - CANCELLED: 已取消
    """

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SupplierPrice(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    供應商商品報價模型

    記錄供應商對商品的報價資訊，支援不同供應商的價格比較。

    欄位：
    - id: 主鍵
    - supplier_id: 供應商 ID
    - product_id: 商品 ID
    - unit_price: 單價
    - min_order_quantity: 最小訂購數量
    - lead_time_days: 交貨天數
    - effective_date: 生效日期
    - expiry_date: 失效日期
    - notes: 備註
    - is_active: 是否啟用

    關聯：
    - supplier: 供應商
    - product: 商品
    """

    __tablename__ = "supplier_prices"

    id: Optional[int] = Field(default=None, primary_key=True)
    unit_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    min_order_quantity: int = Field(
        default=1,
        ge=1,
        description="最小訂購數量",
    )
    lead_time_days: int = Field(
        default=1,
        ge=0,
        description="交貨天數",
    )
    effective_date: date = Field(
        default_factory=lambda: datetime.now(timezone.utc).date(),
        description="生效日期",
    )
    expiry_date: Optional[date] = Field(
        default=None,
        description="失效日期",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    supplier_id: int = Field(
        foreign_key="suppliers.id",
        description="供應商 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    supplier: Optional["Supplier"] = Relationship(back_populates="supplier_prices")
    product: Optional["Product"] = Relationship(back_populates="supplier_prices")

    @property
    def is_valid(self) -> bool:
        """檢查報價是否在有效期內"""
        today = datetime.now(timezone.utc).date()
        if self.effective_date > today:
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        return self.is_active

    def __repr__(self) -> str:
        return f"<SupplierPrice supplier={self.supplier_id} product={self.product_id} price={self.unit_price}>"


class PurchaseOrder(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    採購單模型

    記錄向供應商採購商品的訂單資訊。

    欄位：
    - id: 主鍵
    - order_number: 採購單號（唯一）
    - supplier_id: 供應商 ID
    - warehouse_id: 倉庫 ID
    - order_date: 採購日期
    - expected_date: 預計到貨日期
    - status: 採購單狀態
    - total_amount: 總金額
    - notes: 備註

    關聯：
    - supplier: 供應商
    - warehouse: 倉庫
    - items: 採購單明細
    - receipts: 驗收單
    """

    __tablename__ = "purchase_orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="採購單號",
    )
    order_date: date = Field(
        default_factory=lambda: date.today(),
        description="採購日期",
    )
    expected_date: Optional[date] = Field(
        default=None,
        description="預計到貨日期",
    )
    status: PurchaseOrderStatus = Field(
        default=PurchaseOrderStatus.DRAFT,
        description="採購單狀態",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總金額",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    approved_by: Optional[int] = Field(default=None, description="核准者 ID")
    approved_at: Optional[datetime] = Field(default=None, description="核准時間")

    # 外鍵
    supplier_id: int = Field(
        foreign_key="suppliers.id",
        description="供應商 ID",
    )
    warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="倉庫 ID",
    )

    # 關聯
    supplier: Optional["Supplier"] = Relationship(back_populates="purchase_orders")
    warehouse: Optional["Warehouse"] = Relationship(back_populates="purchase_orders")
    items: List["PurchaseOrderItem"] = Relationship(
        back_populates="purchase_order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    receipts: List["PurchaseReceipt"] = Relationship(back_populates="purchase_order")

    def submit(self) -> None:
        """提交採購單"""
        if self.status == PurchaseOrderStatus.DRAFT:
            self.status = PurchaseOrderStatus.PENDING

    def approve(self, approved_by: int) -> None:
        """核准採購單"""
        if self.status == PurchaseOrderStatus.PENDING:
            self.status = PurchaseOrderStatus.APPROVED
            self.approved_by = approved_by
            self.approved_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消採購單"""
        if self.status in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING):
            self.status = PurchaseOrderStatus.CANCELLED

    def calculate_total(self) -> None:
        """計算總金額"""
        self.total_amount = sum(item.subtotal for item in self.items)

    @property
    def item_count(self) -> int:
        """取得採購項目數量"""
        return len(self.items)

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.order_number}>"


class PurchaseOrderItem(TimestampMixin, table=True):
    """
    採購單明細模型

    記錄採購單中每個商品的採購資訊。

    欄位：
    - id: 主鍵
    - purchase_order_id: 採購單 ID
    - product_id: 商品 ID
    - quantity: 採購數量
    - unit_price: 單價
    - received_quantity: 已收貨數量
    - notes: 備註

    關聯：
    - purchase_order: 採購單
    - product: 商品
    """

    __tablename__ = "purchase_order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(ge=1, description="採購數量")
    unit_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    received_quantity: int = Field(default=0, ge=0, description="已收貨數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    # 外鍵
    purchase_order_id: int = Field(
        foreign_key="purchase_orders.id",
        description="採購單 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    purchase_order: Optional["PurchaseOrder"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="purchase_order_items")

    @property
    def subtotal(self) -> Decimal:
        """計算小計"""
        return self.unit_price * self.quantity

    @property
    def pending_quantity(self) -> int:
        """計算待收貨數量"""
        return self.quantity - self.received_quantity

    def __repr__(self) -> str:
        return f"<PurchaseOrderItem product={self.product_id} qty={self.quantity}>"


class PurchaseReceipt(TimestampMixin, AuditMixin, table=True):
    """
    驗收單模型

    記錄採購單的驗收資訊。

    欄位：
    - id: 主鍵
    - receipt_number: 驗收單號（唯一）
    - purchase_order_id: 採購單 ID
    - receipt_date: 驗收日期
    - status: 驗收單狀態
    - notes: 備註

    關聯：
    - purchase_order: 採購單
    - items: 驗收單明細
    """

    __tablename__ = "purchase_receipts"

    id: Optional[int] = Field(default=None, primary_key=True)
    receipt_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="驗收單號",
    )
    receipt_date: date = Field(
        default_factory=lambda: date.today(),
        description="驗收日期",
    )
    status: PurchaseReceiptStatus = Field(
        default=PurchaseReceiptStatus.PENDING,
        description="驗收單狀態",
    )
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    completed_by: Optional[int] = Field(default=None, description="完成者 ID")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")

    # 外鍵
    purchase_order_id: int = Field(
        foreign_key="purchase_orders.id",
        description="採購單 ID",
    )

    # 關聯
    purchase_order: Optional["PurchaseOrder"] = Relationship(back_populates="receipts")
    items: List["PurchaseReceiptItem"] = Relationship(
        back_populates="purchase_receipt",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def complete(self, completed_by: int) -> None:
        """完成驗收"""
        if self.status == PurchaseReceiptStatus.PENDING:
            self.status = PurchaseReceiptStatus.COMPLETED
            self.completed_by = completed_by
            self.completed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消驗收單"""
        if self.status == PurchaseReceiptStatus.PENDING:
            self.status = PurchaseReceiptStatus.CANCELLED

    @property
    def total_quantity(self) -> int:
        """計算總驗收數量"""
        return sum(item.received_quantity for item in self.items)

    def __repr__(self) -> str:
        return f"<PurchaseReceipt {self.receipt_number}>"


class PurchaseReceiptItem(TimestampMixin, table=True):
    """
    驗收單明細模型

    記錄驗收單中每個商品的驗收資訊。

    欄位：
    - id: 主鍵
    - purchase_receipt_id: 驗收單 ID
    - purchase_order_item_id: 採購單明細 ID
    - product_id: 商品 ID
    - received_quantity: 驗收數量
    - rejected_quantity: 退回數量
    - notes: 備註

    關聯：
    - purchase_receipt: 驗收單
    - product: 商品
    """

    __tablename__ = "purchase_receipt_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    received_quantity: int = Field(ge=0, description="驗收數量")
    rejected_quantity: int = Field(default=0, ge=0, description="退回數量")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    # 外鍵
    purchase_receipt_id: int = Field(
        foreign_key="purchase_receipts.id",
        description="驗收單 ID",
    )
    purchase_order_item_id: Optional[int] = Field(
        default=None,
        foreign_key="purchase_order_items.id",
        description="採購單明細 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    purchase_receipt: Optional["PurchaseReceipt"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="purchase_receipt_items")

    def __repr__(self) -> str:
        return f"<PurchaseReceiptItem product={self.product_id} qty={self.received_quantity}>"


class PurchaseReturn(TimestampMixin, AuditMixin, table=True):
    """
    退貨單模型

    記錄向供應商退貨的資訊。

    欄位：
    - id: 主鍵
    - return_number: 退貨單號（唯一）
    - supplier_id: 供應商 ID
    - warehouse_id: 倉庫 ID
    - purchase_order_id: 原採購單 ID（可選）
    - return_date: 退貨日期
    - status: 退貨單狀態
    - total_amount: 總金額
    - reason: 退貨原因
    - notes: 備註

    關聯：
    - supplier: 供應商
    - warehouse: 倉庫
    - items: 退貨單明細
    """

    __tablename__ = "purchase_returns"

    id: Optional[int] = Field(default=None, primary_key=True)
    return_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="退貨單號",
    )
    return_date: date = Field(
        default_factory=lambda: date.today(),
        description="退貨日期",
    )
    status: PurchaseReturnStatus = Field(
        default=PurchaseReturnStatus.DRAFT,
        description="退貨單狀態",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        description="總金額",
    )
    reason: Optional[str] = Field(default=None, max_length=200, description="退貨原因")
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")
    approved_by: Optional[int] = Field(default=None, description="核准者 ID")
    approved_at: Optional[datetime] = Field(default=None, description="核准時間")

    # 外鍵
    supplier_id: int = Field(
        foreign_key="suppliers.id",
        description="供應商 ID",
    )
    warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="倉庫 ID",
    )
    purchase_order_id: Optional[int] = Field(
        default=None,
        foreign_key="purchase_orders.id",
        description="原採購單 ID",
    )

    # 關聯
    supplier: Optional["Supplier"] = Relationship(back_populates="purchase_returns")
    warehouse: Optional["Warehouse"] = Relationship(back_populates="purchase_returns")
    items: List["PurchaseReturnItem"] = Relationship(
        back_populates="purchase_return",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def submit(self) -> None:
        """提交退貨單"""
        if self.status == PurchaseReturnStatus.DRAFT:
            self.status = PurchaseReturnStatus.PENDING

    def approve(self, approved_by: int) -> None:
        """核准退貨單"""
        if self.status == PurchaseReturnStatus.PENDING:
            self.status = PurchaseReturnStatus.APPROVED
            self.approved_by = approved_by
            self.approved_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """完成退貨"""
        if self.status == PurchaseReturnStatus.APPROVED:
            self.status = PurchaseReturnStatus.COMPLETED

    def cancel(self) -> None:
        """取消退貨單"""
        if self.status in (PurchaseReturnStatus.DRAFT, PurchaseReturnStatus.PENDING):
            self.status = PurchaseReturnStatus.CANCELLED

    def calculate_total(self) -> None:
        """計算總金額"""
        self.total_amount = sum(item.subtotal for item in self.items)

    @property
    def item_count(self) -> int:
        """取得退貨項目數量"""
        return len(self.items)

    def __repr__(self) -> str:
        return f"<PurchaseReturn {self.return_number}>"


class PurchaseReturnItem(TimestampMixin, table=True):
    """
    退貨單明細模型

    記錄退貨單中每個商品的退貨資訊。

    欄位：
    - id: 主鍵
    - purchase_return_id: 退貨單 ID
    - product_id: 商品 ID
    - quantity: 退貨數量
    - unit_price: 單價
    - reason: 退貨原因
    - notes: 備註

    關聯：
    - purchase_return: 退貨單
    - product: 商品
    """

    __tablename__ = "purchase_return_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(ge=1, description="退貨數量")
    unit_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    reason: Optional[str] = Field(default=None, max_length=200, description="退貨原因")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    # 外鍵
    purchase_return_id: int = Field(
        foreign_key="purchase_returns.id",
        description="退貨單 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    purchase_return: Optional["PurchaseReturn"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="purchase_return_items")

    @property
    def subtotal(self) -> Decimal:
        """計算小計"""
        return self.unit_price * self.quantity

    def __repr__(self) -> str:
        return f"<PurchaseReturnItem product={self.product_id} qty={self.quantity}>"
