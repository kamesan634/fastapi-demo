"""
價格管理模型

定義量販價與促銷價的資料模型。

模型：
- VolumePricing: 量販價設定（數量階梯價）
- ProductPromoPrice: 商品促銷價（限時特價）
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product


class VolumePricing(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    量販價設定模型

    依購買數量設定階梯價格。

    欄位：
    - id: 主鍵
    - product_id: 商品 ID
    - min_quantity: 最低數量（達到此數量適用）
    - max_quantity: 最高數量（NULL 表示無上限）
    - unit_price: 單價
    - is_active: 是否啟用

    範例：
    | 數量區間 | 單價 |
    |---------|-----:|
    | 1-9 件  | $299 |
    | 10-49 件| $269 |
    | 50+ 件  | $249 |

    關聯：
    - product: 商品
    """

    __tablename__ = "volume_pricings"

    id: Optional[int] = Field(default=None, primary_key=True)
    min_quantity: int = Field(ge=1, description="最低數量")
    max_quantity: Optional[int] = Field(default=None, ge=1, description="最高數量")
    unit_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="單價",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    product: Optional["Product"] = Relationship(back_populates="volume_pricings")

    def is_applicable(self, quantity: int) -> bool:
        """檢查數量是否適用此價格"""
        if quantity < self.min_quantity:
            return False
        if self.max_quantity and quantity > self.max_quantity:
            return False
        return self.is_active

    def __repr__(self) -> str:
        max_str = str(self.max_quantity) if self.max_quantity else "∞"
        return f"<VolumePricing {self.min_quantity}-{max_str}: ${self.unit_price}>"


class ProductPromoPrice(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    商品促銷價模型

    設定商品的限時特價。

    欄位：
    - id: 主鍵
    - product_id: 商品 ID
    - promo_price: 促銷價格
    - start_date: 開始日期
    - end_date: 結束日期
    - applicable_stores: 適用門市（JSON，NULL 表示全門市）
    - is_active: 是否啟用

    關聯：
    - product: 商品
    """

    __tablename__ = "product_promo_prices"

    id: Optional[int] = Field(default=None, primary_key=True)
    promo_price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="促銷價格",
    )
    start_date: datetime = Field(description="開始日期")
    end_date: datetime = Field(description="結束日期")
    applicable_stores: Optional[str] = Field(
        default=None,
        max_length=500,
        description="適用門市（JSON 格式，NULL 表示全門市）",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 外鍵
    product_id: int = Field(
        foreign_key="products.id",
        description="商品 ID",
    )

    # 關聯
    product: Optional["Product"] = Relationship(back_populates="promo_prices")

    @property
    def is_valid(self) -> bool:
        """檢查促銷價是否在有效期內"""
        now = datetime.now(timezone.utc)
        return self.is_active and self.start_date <= now <= self.end_date

    def __repr__(self) -> str:
        return f"<ProductPromoPrice ${self.promo_price} ({self.start_date} - {self.end_date})>"
