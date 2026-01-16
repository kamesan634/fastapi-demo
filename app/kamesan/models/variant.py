"""
商品規格模型

定義商品規格類型與規格變體的資料模型。

模型：
- ProductSpecification: 商品規格定義（如：顏色、尺寸）
- ProductVariant: 商品規格變體（具體 SKU）
"""

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product


class ProductSpecification(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    商品規格定義模型

    定義商品可用的規格類型（如顏色、尺寸）及其選項。

    欄位：
    - id: 主鍵
    - product_id: 商品 ID
    - name: 規格名稱（如：顏色、尺寸）
    - options: 規格選項（JSON 陣列，如：["白色", "黑色", "灰色"]）
    - sort_order: 排序順序
    - is_active: 是否啟用

    關聯：
    - product: 商品
    """

    __tablename__ = "product_specifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, description="規格名稱")
    options: List[str] = Field(default=[], sa_column=Column(JSON), description="規格選項")
    sort_order: int = Field(default=0, description="排序順序")
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    product: Optional["Product"] = Relationship(back_populates="specifications")

    def __repr__(self) -> str:
        return f"<ProductSpecification {self.name}: {self.options}>"


class ProductVariant(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    商品規格變體模型

    記錄商品的具體規格組合（SKU）。

    欄位：
    - id: 主鍵
    - product_id: 父商品 ID
    - sku: SKU 編號（唯一）
    - barcode: 條碼
    - variant_options: 規格組合（JSON，如：{"顏色": "白色", "尺寸": "M"}）
    - cost_price: 成本價（可覆寫主商品價格）
    - selling_price: 售價（可覆寫主商品價格）
    - image_url: 圖片 URL
    - stock_quantity: 庫存數量（冗餘欄位，方便查詢）
    - is_active: 是否啟用

    關聯：
    - product: 父商品
    """

    __tablename__ = "product_variants"

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(
        max_length=50,
        unique=True,
        index=True,
        description="SKU 編號",
    )
    barcode: Optional[str] = Field(
        default=None,
        max_length=50,
        unique=True,
        index=True,
        description="條碼",
    )
    variant_options: dict = Field(default={}, sa_column=Column(JSON), description="規格組合")
    cost_price: Optional[Decimal] = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="成本價",
    )
    selling_price: Optional[Decimal] = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="售價",
    )
    image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="圖片 URL",
    )
    stock_quantity: int = Field(default=0, description="庫存數量")
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    product: Optional["Product"] = Relationship(back_populates="variants")

    @property
    def effective_cost_price(self) -> Decimal:
        """取得有效成本價（優先使用變體價格，否則使用父商品價格）"""
        if self.cost_price is not None:
            return self.cost_price
        return self.product.cost_price if self.product else Decimal("0")

    @property
    def effective_selling_price(self) -> Decimal:
        """取得有效售價（優先使用變體價格，否則使用父商品價格）"""
        if self.selling_price is not None:
            return self.selling_price
        return self.product.selling_price if self.product else Decimal("0")

    @property
    def variant_name(self) -> str:
        """取得規格名稱（如：白色-M）"""
        if not self.variant_options:
            return ""
        return "-".join(str(v) for v in self.variant_options.values())

    def __repr__(self) -> str:
        return f"<ProductVariant {self.sku}>"
