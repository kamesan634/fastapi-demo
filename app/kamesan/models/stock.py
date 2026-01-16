"""
庫存盤點與庫存調撥模型

定義庫存盤點、盤點明細、庫存調撥、調撥明細等資料模型。

模型：
- StockCount: 庫存盤點單
- StockCountItem: 庫存盤點明細
- StockTransfer: 庫存調撥單
- StockTransferItem: 庫存調撥明細
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product
    from app.kamesan.models.store import Warehouse


class StockCountStatus(str, Enum):
    """
    庫存盤點狀態

    狀態說明：
    - DRAFT: 草稿（盤點單建立但尚未開始）
    - IN_PROGRESS: 進行中（盤點正在執行）
    - COMPLETED: 已完成（盤點完成並已確認）
    - CANCELLED: 已取消（盤點單被取消）
    """

    DRAFT = "DRAFT"  # 草稿
    IN_PROGRESS = "IN_PROGRESS"  # 進行中
    COMPLETED = "COMPLETED"  # 已完成
    CANCELLED = "CANCELLED"  # 已取消


class StockTransferStatus(str, Enum):
    """
    庫存調撥狀態

    狀態說明：
    - DRAFT: 草稿（調撥單建立但尚未提交）
    - PENDING: 待審核（調撥單已提交，等待審核）
    - APPROVED: 已核准（調撥單已核准，等待出貨）
    - IN_TRANSIT: 運送中（商品已從來源倉庫出貨）
    - COMPLETED: 已完成（商品已到達目的倉庫並確認收貨）
    - CANCELLED: 已取消（調撥單被取消）
    """

    DRAFT = "DRAFT"  # 草稿
    PENDING = "PENDING"  # 待審核
    APPROVED = "APPROVED"  # 已核准
    IN_TRANSIT = "IN_TRANSIT"  # 運送中
    COMPLETED = "COMPLETED"  # 已完成
    CANCELLED = "CANCELLED"  # 已取消


class StockCount(TimestampMixin, table=True):
    """
    庫存盤點單模型

    記錄倉庫的庫存盤點作業。

    欄位：
    - id: 主鍵
    - count_number: 盤點單號（唯一）
    - warehouse_id: 倉庫 ID
    - count_date: 盤點日期
    - status: 盤點狀態
    - notes: 備註
    - created_by: 建立者 ID
    - completed_by: 完成者 ID
    - completed_at: 完成時間

    關聯：
    - warehouse: 倉庫
    - items: 盤點明細列表
    """

    __tablename__ = "stock_counts"

    id: Optional[int] = Field(default=None, primary_key=True)
    count_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="盤點單號",
    )
    count_date: date = Field(
        default_factory=lambda: date.today(),
        description="盤點日期",
    )
    status: StockCountStatus = Field(
        default=StockCountStatus.DRAFT,
        description="盤點狀態",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    created_by: Optional[int] = Field(
        default=None,
        description="建立者 ID",
    )
    completed_by: Optional[int] = Field(
        default=None,
        description="完成者 ID",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="完成時間",
    )

    # 外鍵
    warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="倉庫 ID",
    )

    # 關聯
    warehouse: Optional["Warehouse"] = Relationship(
        back_populates="stock_counts",
    )
    items: List["StockCountItem"] = Relationship(
        back_populates="stock_count",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def start(self) -> None:
        """開始盤點"""
        if self.status == StockCountStatus.DRAFT:
            self.status = StockCountStatus.IN_PROGRESS

    def complete(self, completed_by: int) -> None:
        """完成盤點"""
        if self.status == StockCountStatus.IN_PROGRESS:
            self.status = StockCountStatus.COMPLETED
            self.completed_by = completed_by
            self.completed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消盤點"""
        if self.status in (StockCountStatus.DRAFT, StockCountStatus.IN_PROGRESS):
            self.status = StockCountStatus.CANCELLED

    @property
    def total_difference(self) -> int:
        """計算總差異數量"""
        return sum(item.difference for item in self.items)

    @property
    def item_count(self) -> int:
        """取得盤點項目數量"""
        return len(self.items)

    def __repr__(self) -> str:
        return f"<StockCount {self.count_number}>"


class StockCountItem(TimestampMixin, table=True):
    """
    庫存盤點明細模型

    記錄盤點單中每個商品的盤點資訊。

    欄位：
    - id: 主鍵
    - stock_count_id: 盤點單 ID
    - product_id: 商品 ID
    - system_quantity: 系統數量（盤點時的帳面庫存）
    - actual_quantity: 實際數量（盤點清點的數量）
    - difference: 差異數量（實際 - 系統）
    - notes: 備註

    關聯：
    - stock_count: 盤點單
    - product: 商品
    """

    __tablename__ = "stock_count_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    system_quantity: int = Field(
        default=0,
        description="系統數量",
    )
    actual_quantity: int = Field(
        default=0,
        description="實際數量",
    )
    difference: int = Field(
        default=0,
        description="差異數量",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="備註",
    )

    # 外鍵
    stock_count_id: int = Field(
        foreign_key="stock_counts.id",
        description="盤點單 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    stock_count: Optional["StockCount"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="stock_count_items")

    def calculate_difference(self) -> None:
        """計算差異數量"""
        self.difference = self.actual_quantity - self.system_quantity

    def __repr__(self) -> str:
        return f"<StockCountItem product={self.product_id} diff={self.difference}>"


class StockTransfer(TimestampMixin, table=True):
    """
    庫存調撥單模型

    記錄倉庫間的庫存調撥作業。

    欄位：
    - id: 主鍵
    - transfer_number: 調撥單號（唯一）
    - source_warehouse_id: 來源倉庫 ID
    - destination_warehouse_id: 目的倉庫 ID
    - transfer_date: 調撥日期
    - expected_date: 預計到達日期
    - received_date: 實際收貨日期
    - status: 調撥狀態
    - notes: 備註
    - created_by: 建立者 ID
    - approved_by: 核准者 ID
    - approved_at: 核准時間
    - received_by: 收貨者 ID

    關聯：
    - source_warehouse: 來源倉庫
    - destination_warehouse: 目的倉庫
    - items: 調撥明細列表
    """

    __tablename__ = "stock_transfers"

    id: Optional[int] = Field(default=None, primary_key=True)
    transfer_number: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="調撥單號",
    )
    transfer_date: date = Field(
        default_factory=lambda: date.today(),
        description="調撥日期",
    )
    expected_date: Optional[date] = Field(
        default=None,
        description="預計到達日期",
    )
    received_date: Optional[date] = Field(
        default=None,
        description="實際收貨日期",
    )
    status: StockTransferStatus = Field(
        default=StockTransferStatus.DRAFT,
        description="調撥狀態",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    created_by: Optional[int] = Field(
        default=None,
        description="建立者 ID",
    )
    approved_by: Optional[int] = Field(
        default=None,
        description="核准者 ID",
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        description="核准時間",
    )
    received_by: Optional[int] = Field(
        default=None,
        description="收貨者 ID",
    )

    # 外鍵
    source_warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="來源倉庫 ID",
    )
    destination_warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="目的倉庫 ID",
    )

    # 關聯
    source_warehouse: Optional["Warehouse"] = Relationship(
        back_populates="outgoing_transfers",
        sa_relationship_kwargs={"foreign_keys": "[StockTransfer.source_warehouse_id]"},
    )
    destination_warehouse: Optional["Warehouse"] = Relationship(
        back_populates="incoming_transfers",
        sa_relationship_kwargs={"foreign_keys": "[StockTransfer.destination_warehouse_id]"},
    )
    items: List["StockTransferItem"] = Relationship(
        back_populates="stock_transfer",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def submit(self) -> None:
        """提交調撥單"""
        if self.status == StockTransferStatus.DRAFT:
            self.status = StockTransferStatus.PENDING

    def approve(self, approved_by: int) -> None:
        """核准調撥單"""
        if self.status == StockTransferStatus.PENDING:
            self.status = StockTransferStatus.APPROVED
            self.approved_by = approved_by
            self.approved_at = datetime.now(timezone.utc)

    def ship(self) -> None:
        """出貨（開始運送）"""
        if self.status == StockTransferStatus.APPROVED:
            self.status = StockTransferStatus.IN_TRANSIT

    def receive(self, received_by: int) -> None:
        """收貨完成"""
        if self.status == StockTransferStatus.IN_TRANSIT:
            self.status = StockTransferStatus.COMPLETED
            self.received_by = received_by
            self.received_date = date.today()

    def cancel(self) -> None:
        """取消調撥單"""
        if self.status in (
            StockTransferStatus.DRAFT,
            StockTransferStatus.PENDING,
            StockTransferStatus.APPROVED,
        ):
            self.status = StockTransferStatus.CANCELLED

    @property
    def total_quantity(self) -> int:
        """計算總調撥數量"""
        return sum(item.quantity for item in self.items)

    @property
    def total_received_quantity(self) -> int:
        """計算總收貨數量"""
        return sum(item.received_quantity or 0 for item in self.items)

    @property
    def item_count(self) -> int:
        """取得調撥項目數量"""
        return len(self.items)

    def __repr__(self) -> str:
        return f"<StockTransfer {self.transfer_number}>"


class StockTransferItem(TimestampMixin, table=True):
    """
    庫存調撥明細模型

    記錄調撥單中每個商品的調撥資訊。

    欄位：
    - id: 主鍵
    - stock_transfer_id: 調撥單 ID
    - product_id: 商品 ID
    - quantity: 調撥數量
    - received_quantity: 實際收貨數量
    - notes: 備註

    關聯：
    - stock_transfer: 調撥單
    - product: 商品
    """

    __tablename__ = "stock_transfer_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(
        default=0,
        ge=0,
        description="調撥數量",
    )
    received_quantity: Optional[int] = Field(
        default=None,
        ge=0,
        description="實際收貨數量",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="備註",
    )

    # 外鍵
    stock_transfer_id: int = Field(
        foreign_key="stock_transfers.id",
        description="調撥單 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    stock_transfer: Optional["StockTransfer"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="stock_transfer_items")

    @property
    def shortage(self) -> int:
        """計算短少數量（調撥數量 - 實際收貨數量）"""
        if self.received_quantity is not None:
            return self.quantity - self.received_quantity
        return 0

    def __repr__(self) -> str:
        return f"<StockTransferItem product={self.product_id} qty={self.quantity}>"
