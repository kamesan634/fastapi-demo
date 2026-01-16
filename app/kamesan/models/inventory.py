"""
庫存模型

定義庫存與庫存異動記錄的資料模型。

模型：
- Inventory: 庫存（各倉庫的商品庫存）
- InventoryTransaction: 庫存異動記錄
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product
    from app.kamesan.models.store import Warehouse


class TransactionType(str, Enum):
    """庫存異動類型"""

    PURCHASE = "PURCHASE"  # 進貨
    SALE = "SALE"  # 銷售
    RETURN = "RETURN"  # 退貨
    ADJUSTMENT = "ADJUSTMENT"  # 調整
    TRANSFER_IN = "TRANSFER_IN"  # 調撥入庫
    TRANSFER_OUT = "TRANSFER_OUT"  # 調撥出庫
    DAMAGE = "DAMAGE"  # 報廢


class Inventory(TimestampMixin, table=True):
    """
    庫存模型

    記錄各倉庫中商品的庫存數量。

    欄位：
    - id: 主鍵
    - product_id: 商品 ID
    - warehouse_id: 倉庫 ID
    - quantity: 庫存數量
    - reserved_quantity: 保留數量（已下單未出貨）
    - last_stock_date: 最後盤點日期

    關聯：
    - product: 商品
    - warehouse: 倉庫

    唯一約束：
    - (product_id, warehouse_id): 同一倉庫同一商品只能有一筆庫存記錄
    """

    __tablename__ = "inventories"

    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(default=0, description="庫存數量")
    reserved_quantity: int = Field(default=0, description="保留數量")
    last_stock_date: Optional[datetime] = Field(
        default=None,
        description="最後盤點日期",
    )

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )
    warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="倉庫 ID",
    )

    # 關聯
    product: Optional["Product"] = Relationship(back_populates="inventories")
    warehouse: Optional["Warehouse"] = Relationship(back_populates="inventories")

    @property
    def available_quantity(self) -> int:
        """可用庫存數量（實際庫存 - 保留數量）"""
        return self.quantity - self.reserved_quantity

    def add_stock(self, quantity: int) -> None:
        """增加庫存"""
        self.quantity += quantity

    def reduce_stock(self, quantity: int) -> bool:
        """減少庫存"""
        if self.available_quantity >= quantity:
            self.quantity -= quantity
            return True
        return False

    def reserve(self, quantity: int) -> bool:
        """保留庫存"""
        if self.available_quantity >= quantity:
            self.reserved_quantity += quantity
            return True
        return False

    def release_reserve(self, quantity: int) -> None:
        """釋放保留庫存"""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} warehouse={self.warehouse_id} qty={self.quantity}>"


class InventoryTransaction(TimestampMixin, table=True):
    """
    庫存異動記錄模型

    記錄所有庫存的變動歷史。

    欄位：
    - id: 主鍵
    - product_id: 商品 ID
    - warehouse_id: 倉庫 ID
    - transaction_type: 異動類型
    - quantity: 異動數量（正數=入庫, 負數=出庫）
    - before_quantity: 異動前數量
    - after_quantity: 異動後數量
    - reference_type: 參考單據類型
    - reference_id: 參考單據 ID
    - notes: 備註
    - created_by: 建立者 ID
    """

    __tablename__ = "inventory_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_type: TransactionType = Field(description="異動類型")
    quantity: int = Field(description="異動數量")
    before_quantity: int = Field(description="異動前數量")
    after_quantity: int = Field(description="異動後數量")
    reference_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="參考單據類型",
    )
    reference_id: Optional[int] = Field(
        default=None,
        description="參考單據 ID",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="備註",
    )
    created_by: Optional[int] = Field(
        default=None,
        description="建立者 ID",
    )

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )
    warehouse_id: int = Field(
        foreign_key="warehouses.id",
        description="倉庫 ID",
    )

    def __repr__(self) -> str:
        return f"<InventoryTransaction {self.transaction_type} qty={self.quantity}>"
