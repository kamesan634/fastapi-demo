"""
商品組合/套餐模型

定義商品組合與套餐的資料模型。

模型：
- ProductCombo: 商品組合/套餐
- ProductComboItem: 組合內的商品項目
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product


class ComboType(str, Enum):
    """組合類型"""

    FIXED = "FIXED"  # 固定組合：固定商品組成
    FLEXIBLE = "FLEXIBLE"  # 自選組合：可從選項中挑選


class ProductCombo(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    商品組合/套餐模型

    建立商品組合銷售，支援套餐優惠。

    欄位：
    - id: 主鍵
    - code: 組合編號（唯一）
    - name: 組合名稱
    - combo_type: 組合類型（固定/自選）
    - combo_price: 組合售價
    - original_price: 原價總計（單買總價）
    - min_select_count: 最少選擇數量（自選組合用）
    - max_select_count: 最多選擇數量（自選組合用）
    - start_date: 開始日期
    - end_date: 結束日期
    - description: 描述
    - image_url: 圖片 URL
    - is_active: 是否啟用

    關聯：
    - items: 組合內的商品項目
    """

    __tablename__ = "product_combos"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=30,
        unique=True,
        index=True,
        description="組合編號",
    )
    name: str = Field(max_length=100, description="組合名稱")
    combo_type: ComboType = Field(
        default=ComboType.FIXED,
        description="組合類型",
    )
    combo_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="組合售價",
    )
    original_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="原價總計",
    )
    min_select_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="最少選擇數量",
    )
    max_select_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="最多選擇數量",
    )
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="描述",
    )
    image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="圖片 URL",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    items: List["ProductComboItem"] = Relationship(
        back_populates="combo",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def savings(self) -> Decimal:
        """計算省下的金額"""
        return self.original_price - self.combo_price

    @property
    def discount_percentage(self) -> Decimal:
        """計算折扣百分比"""
        if self.original_price > 0:
            return round((1 - self.combo_price / self.original_price) * 100, 2)
        return Decimal("0")

    @property
    def is_valid(self) -> bool:
        """檢查組合是否在有效期內"""
        if not self.is_active:
            return False
        today = date.today()
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    def __repr__(self) -> str:
        return f"<ProductCombo {self.code}: {self.name}>"


class ProductComboItem(TimestampMixin, table=True):
    """
    組合商品項目模型

    記錄組合內的商品與數量。

    欄位：
    - id: 主鍵
    - combo_id: 組合 ID
    - product_id: 商品 ID
    - quantity: 數量
    - is_required: 是否必選（自選組合用）
    - is_default: 是否預設選擇
    - sort_order: 排序順序
    - notes: 備註

    關聯：
    - combo: 所屬組合
    - product: 商品
    """

    __tablename__ = "product_combo_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(default=1, ge=1, description="數量")
    is_required: bool = Field(default=True, description="是否必選")
    is_default: bool = Field(default=False, description="是否預設選擇")
    sort_order: int = Field(default=0, description="排序順序")
    notes: Optional[str] = Field(default=None, max_length=200, description="備註")

    # 外鍵
    combo_id: int = Field(
        foreign_key="product_combos.id",
        description="組合 ID",
    )
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    combo: Optional["ProductCombo"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="combo_items")

    def __repr__(self) -> str:
        return f"<ProductComboItem product={self.product_id} qty={self.quantity}>"
