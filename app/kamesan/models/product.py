"""
商品相關模型

定義商品、類別、單位、稅別等資料模型。

模型：
- Category: 商品類別
- TaxType: 稅別
- Unit: 計量單位
- Product: 商品
"""

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.combo import ProductComboItem
    from app.kamesan.models.inventory import Inventory
    from app.kamesan.models.order import OrderItem, SalesReturnItem
    from app.kamesan.models.pricing import ProductPromoPrice, VolumePricing
    from app.kamesan.models.purchase import (
        PurchaseOrderItem,
        PurchaseReceiptItem,
        PurchaseReturnItem,
        SupplierPrice,
    )
    from app.kamesan.models.stock import StockCountItem, StockTransferItem
    from app.kamesan.models.supplier import Supplier
    from app.kamesan.models.variant import ProductSpecification, ProductVariant


class Category(TimestampMixin, SoftDeleteMixin, table=True):
    """
    商品類別模型

    商品分類，支援多層級結構。

    欄位：
    - id: 主鍵
    - code: 類別代碼（唯一）
    - name: 類別名稱
    - parent_id: 上層類別 ID（支援多層級）
    - level: 類別層級（1=主類別, 2=子類別...）
    - sort_order: 排序順序
    - is_active: 是否啟用

    關聯：
    - parent: 上層類別
    - children: 下層類別列表
    - products: 此類別的商品列表
    """

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="類別代碼",
    )
    name: str = Field(max_length=50, description="類別名稱")
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="categories.id",
        description="上層類別 ID",
    )
    level: int = Field(default=1, description="類別層級")
    sort_order: int = Field(default=0, description="排序順序")
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"},
    )
    children: List["Category"] = Relationship(back_populates="parent")
    products: List["Product"] = Relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.code}: {self.name}>"


class TaxType(TimestampMixin, table=True):
    """
    稅別模型

    定義不同的稅率類型。

    欄位：
    - id: 主鍵
    - code: 稅別代碼（唯一）
    - name: 稅別名稱
    - rate: 稅率（例如 0.05 = 5%）
    - is_active: 是否啟用

    關聯：
    - products: 使用此稅別的商品列表
    """

    __tablename__ = "tax_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="稅別代碼",
    )
    name: str = Field(max_length=50, description="稅別名稱")
    rate: Decimal = Field(
        default=Decimal("0.05"),
        max_digits=5,
        decimal_places=4,
        description="稅率",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    products: List["Product"] = Relationship(back_populates="tax_type")

    def __repr__(self) -> str:
        return f"<TaxType {self.code}: {self.name} ({self.rate})>"


class Unit(TimestampMixin, table=True):
    """
    計量單位模型

    商品的計量單位。

    欄位：
    - id: 主鍵
    - code: 單位代碼（唯一）
    - name: 單位名稱
    - is_active: 是否啟用

    關聯：
    - products: 使用此單位的商品列表
    """

    __tablename__ = "units"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=10,
        unique=True,
        index=True,
        description="單位代碼",
    )
    name: str = Field(max_length=20, description="單位名稱")
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    products: List["Product"] = Relationship(back_populates="unit")

    def __repr__(self) -> str:
        return f"<Unit {self.code}: {self.name}>"


class Product(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    商品模型

    商品主檔，記錄商品的基本資訊與定價。

    欄位：
    - id: 主鍵
    - code: 商品代碼（唯一）
    - barcode: 商品條碼（唯一）
    - name: 商品名稱
    - description: 商品描述
    - category_id: 類別 ID
    - unit_id: 單位 ID
    - tax_type_id: 稅別 ID
    - supplier_id: 供應商 ID
    - cost_price: 成本價
    - selling_price: 售價
    - min_stock: 最低庫存量
    - max_stock: 最高庫存量
    - is_active: 是否上架

    關聯：
    - category: 商品類別
    - unit: 計量單位
    - tax_type: 稅別
    - supplier: 供應商
    - inventories: 庫存列表
    - order_items: 訂單明細列表
    """

    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="商品代碼",
    )
    barcode: Optional[str] = Field(
        default=None,
        max_length=50,
        unique=True,
        index=True,
        description="商品條碼",
    )
    name: str = Field(max_length=100, description="商品名稱")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="商品描述",
    )
    cost_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="成本價",
    )
    selling_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="售價",
    )
    min_stock: int = Field(default=0, description="最低庫存量")
    max_stock: int = Field(default=0, description="最高庫存量")
    is_active: bool = Field(default=True, description="是否上架")

    # 外鍵
    category_id: Optional[int] = Field(
        default=None,
        foreign_key="categories.id",
        description="類別 ID",
    )
    unit_id: Optional[int] = Field(
        default=None,
        foreign_key="units.id",
        description="單位 ID",
    )
    tax_type_id: Optional[int] = Field(
        default=None,
        foreign_key="tax_types.id",
        description="稅別 ID",
    )
    supplier_id: Optional[int] = Field(
        default=None,
        foreign_key="suppliers.id",
        description="供應商 ID",
    )

    # 關聯
    category: Optional[Category] = Relationship(back_populates="products")
    unit: Optional[Unit] = Relationship(back_populates="products")
    tax_type: Optional[TaxType] = Relationship(back_populates="products")
    supplier: Optional["Supplier"] = Relationship(back_populates="products")
    inventories: List["Inventory"] = Relationship(back_populates="product")
    order_items: List["OrderItem"] = Relationship(back_populates="product")
    supplier_prices: List["SupplierPrice"] = Relationship(back_populates="product")
    purchase_order_items: List["PurchaseOrderItem"] = Relationship(back_populates="product")
    purchase_receipt_items: List["PurchaseReceiptItem"] = Relationship(back_populates="product")
    purchase_return_items: List["PurchaseReturnItem"] = Relationship(back_populates="product")
    stock_count_items: List["StockCountItem"] = Relationship(back_populates="product")
    stock_transfer_items: List["StockTransferItem"] = Relationship(back_populates="product")
    sales_return_items: List["SalesReturnItem"] = Relationship(back_populates="product")
    specifications: List["ProductSpecification"] = Relationship(back_populates="product")
    variants: List["ProductVariant"] = Relationship(back_populates="product")
    volume_pricings: List["VolumePricing"] = Relationship(back_populates="product")
    promo_prices: List["ProductPromoPrice"] = Relationship(back_populates="product")
    combo_items: List["ProductComboItem"] = Relationship(back_populates="product")

    @property
    def profit_margin(self) -> Decimal:
        """計算毛利率"""
        if self.selling_price > 0:
            return (self.selling_price - self.cost_price) / self.selling_price
        return Decimal("0.00")

    def __repr__(self) -> str:
        return f"<Product {self.code}: {self.name}>"
