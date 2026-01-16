"""
供應商模型

定義供應商的資料模型。

模型：
- Supplier: 供應商（商品進貨來源）
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.product import Product
    from app.kamesan.models.purchase import PurchaseOrder, PurchaseReturn, SupplierPrice


class Supplier(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    供應商模型

    商品進貨來源，記錄供應商的基本資料與聯絡方式。

    欄位：
    - id: 主鍵
    - code: 供應商代碼（唯一）
    - name: 供應商名稱
    - contact_name: 聯絡人姓名
    - phone: 電話
    - email: 電子郵件
    - address: 地址
    - tax_id: 統一編號
    - payment_terms: 付款條件（天數）
    - notes: 備註
    - is_active: 是否啟用

    關聯：
    - products: 此供應商的商品列表
    """

    __tablename__ = "suppliers"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="供應商代碼",
    )
    name: str = Field(max_length=100, description="供應商名稱")
    contact_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description="聯絡人姓名",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="電話",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=100,
        description="電子郵件",
    )
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="地址",
    )
    tax_id: Optional[str] = Field(
        default=None,
        max_length=20,
        description="統一編號",
    )
    payment_terms: int = Field(
        default=30,
        description="付款條件（天數）",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="備註",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    products: List["Product"] = Relationship(back_populates="supplier")
    supplier_prices: List["SupplierPrice"] = Relationship(back_populates="supplier")
    purchase_orders: List["PurchaseOrder"] = Relationship(back_populates="supplier")
    purchase_returns: List["PurchaseReturn"] = Relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.code}: {self.name}>"
