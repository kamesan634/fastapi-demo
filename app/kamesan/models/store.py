"""
門市與倉庫模型

定義門市與倉庫的資料模型。

模型：
- Store: 門市（銷售據點）
- Warehouse: 倉庫（庫存儲存地點）
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.inventory import Inventory
    from app.kamesan.models.order import Order
    from app.kamesan.models.purchase import PurchaseOrder, PurchaseReturn
    from app.kamesan.models.stock import StockCount, StockTransfer
    from app.kamesan.models.user import User


class Store(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    門市模型

    代表一個銷售據點，可以有多個員工和訂單。

    欄位：
    - id: 主鍵
    - code: 門市代碼（唯一）
    - name: 門市名稱
    - address: 地址
    - phone: 電話
    - is_active: 是否營業中
    - warehouse_id: 關聯倉庫 ID

    關聯：
    - warehouse: 門市關聯的倉庫
    - users: 門市員工列表
    - orders: 門市的訂單列表
    """

    __tablename__ = "stores"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="門市代碼",
    )
    name: str = Field(max_length=100, description="門市名稱")
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="地址",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="電話",
    )
    is_active: bool = Field(default=True, description="是否營業中")

    # 外鍵
    warehouse_id: Optional[int] = Field(
        default=None,
        foreign_key="warehouses.id",
        description="關聯倉庫 ID",
    )

    # 關聯
    warehouse: Optional["Warehouse"] = Relationship(back_populates="stores")
    users: List["User"] = Relationship(back_populates="store")
    orders: List["Order"] = Relationship(back_populates="store")

    def __repr__(self) -> str:
        return f"<Store {self.code}: {self.name}>"


class Warehouse(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    倉庫模型

    代表一個庫存儲存地點，可以關聯多個門市。

    欄位：
    - id: 主鍵
    - code: 倉庫代碼（唯一）
    - name: 倉庫名稱
    - address: 地址
    - is_active: 是否啟用

    關聯：
    - stores: 關聯此倉庫的門市列表
    - inventories: 此倉庫的庫存列表
    """

    __tablename__ = "warehouses"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="倉庫代碼",
    )
    name: str = Field(max_length=100, description="倉庫名稱")
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="地址",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    stores: List["Store"] = Relationship(back_populates="warehouse")
    inventories: List["Inventory"] = Relationship(back_populates="warehouse")
    stock_counts: List["StockCount"] = Relationship(back_populates="warehouse")
    outgoing_transfers: List["StockTransfer"] = Relationship(
        back_populates="source_warehouse",
        sa_relationship_kwargs={"foreign_keys": "[StockTransfer.source_warehouse_id]"},
    )
    incoming_transfers: List["StockTransfer"] = Relationship(
        back_populates="destination_warehouse",
        sa_relationship_kwargs={"foreign_keys": "[StockTransfer.destination_warehouse_id]"},
    )
    purchase_orders: List["PurchaseOrder"] = Relationship(back_populates="warehouse")
    purchase_returns: List["PurchaseReturn"] = Relationship(back_populates="warehouse")

    def __repr__(self) -> str:
        return f"<Warehouse {self.code}: {self.name}>"
