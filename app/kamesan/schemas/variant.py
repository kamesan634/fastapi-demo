"""
商品規格 Schema

定義商品規格定義與變體的請求與回應格式。
"""

from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ==========================================
# 規格定義 Schema
# ==========================================
class SpecificationBase(BaseModel):
    """規格定義基礎 Schema"""

    name: str = Field(max_length=50, description="規格名稱")
    options: List[str] = Field(min_length=1, description="規格選項")
    sort_order: int = Field(default=0, description="排序順序")


class SpecificationCreate(SpecificationBase):
    """規格定義建立 Schema"""

    pass


class SpecificationUpdate(BaseModel):
    """規格定義更新 Schema"""

    name: Optional[str] = Field(default=None, max_length=50, description="規格名稱")
    options: Optional[List[str]] = Field(default=None, description="規格選項")
    sort_order: Optional[int] = Field(default=None, description="排序順序")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class SpecificationResponse(SpecificationBase):
    """規格定義回應 Schema"""

    id: int
    product_id: int
    is_active: bool

    model_config = {"from_attributes": True}


# ==========================================
# 規格變體 Schema
# ==========================================
class VariantBase(BaseModel):
    """規格變體基礎 Schema"""

    sku: str = Field(max_length=50, description="SKU 編號")
    variant_options: Dict[str, str] = Field(description="規格組合")
    barcode: Optional[str] = Field(default=None, max_length=50, description="條碼")
    cost_price: Optional[Decimal] = Field(default=None, ge=0, description="成本價")
    selling_price: Optional[Decimal] = Field(default=None, ge=0, description="售價")
    image_url: Optional[str] = Field(default=None, max_length=500, description="圖片 URL")


class VariantCreate(VariantBase):
    """規格變體建立 Schema"""

    pass


class VariantUpdate(BaseModel):
    """規格變體更新 Schema"""

    sku: Optional[str] = Field(default=None, max_length=50, description="SKU 編號")
    barcode: Optional[str] = Field(default=None, max_length=50, description="條碼")
    variant_options: Optional[Dict[str, str]] = Field(default=None, description="規格組合")
    cost_price: Optional[Decimal] = Field(default=None, ge=0, description="成本價")
    selling_price: Optional[Decimal] = Field(default=None, ge=0, description="售價")
    image_url: Optional[str] = Field(default=None, max_length=500, description="圖片 URL")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class VariantResponse(VariantBase):
    """規格變體回應 Schema"""

    id: int
    product_id: int
    stock_quantity: int
    is_active: bool
    effective_cost_price: Optional[Decimal] = Field(None, description="有效成本價")
    effective_selling_price: Optional[Decimal] = Field(None, description="有效售價")
    variant_name: str = Field(description="規格名稱")

    model_config = {"from_attributes": True}


class VariantSummaryResponse(BaseModel):
    """規格變體摘要回應 Schema"""

    id: int
    sku: str
    variant_options: Dict[str, str]
    selling_price: Optional[Decimal]
    stock_quantity: int
    is_active: bool

    model_config = {"from_attributes": True}


# ==========================================
# 批次操作 Schema
# ==========================================
class GenerateVariantsRequest(BaseModel):
    """批次產生變體請求 Schema"""

    specifications: List[SpecificationCreate] = Field(
        min_length=1,
        max_length=5,
        description="規格定義列表",
    )
    sku_prefix: Optional[str] = Field(
        default=None,
        max_length=20,
        description="SKU 前綴",
    )
    base_cost_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="基礎成本價",
    )
    base_selling_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="基礎售價",
    )


class GenerateVariantsResponse(BaseModel):
    """批次產生變體回應 Schema"""

    specifications_created: int = Field(description="建立的規格數量")
    variants_created: int = Field(description="建立的變體數量")
    variants: List[VariantSummaryResponse] = Field(description="變體列表")


class BulkVariantCreate(BaseModel):
    """批次建立變體項目 Schema"""

    sku: str = Field(max_length=50, description="SKU 編號")
    variant_options: Dict[str, str] = Field(description="規格組合")
    barcode: Optional[str] = Field(default=None, max_length=50, description="條碼")
    cost_price: Optional[Decimal] = Field(default=None, ge=0, description="成本價")
    selling_price: Optional[Decimal] = Field(default=None, ge=0, description="售價")


class BulkVariantCreateRequest(BaseModel):
    """批次建立變體請求 Schema"""

    variants: List[BulkVariantCreate] = Field(min_length=1, description="變體列表")


class BulkOperationResponse(BaseModel):
    """批次操作回應 Schema"""

    success_count: int = Field(description="成功數量")
    failed_count: int = Field(description="失敗數量")
    errors: List[str] = Field(default=[], description="錯誤訊息列表")
