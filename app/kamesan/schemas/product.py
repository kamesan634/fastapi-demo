"""
商品相關 Schema 模型

定義商品、類別、單位、稅別的請求和回應模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ==========================================
# 稅別模型
# ==========================================
class TaxTypeBase(BaseModel):
    """稅別基礎模型"""

    code: str = Field(max_length=20, description="稅別代碼")
    name: str = Field(max_length=50, description="稅別名稱")
    rate: Decimal = Field(default=Decimal("0.05"), ge=0, le=1, description="稅率")
    is_active: bool = Field(default=True, description="是否啟用")


class TaxTypeCreate(TaxTypeBase):
    """稅別建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "TAX5",
                    "name": "應稅5%",
                    "rate": "0.05",
                    "is_active": True,
                }
            ]
        }
    }


class TaxTypeUpdate(BaseModel):
    """稅別更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="稅別代碼")
    name: Optional[str] = Field(default=None, max_length=50, description="稅別名稱")
    rate: Optional[Decimal] = Field(default=None, ge=0, le=1, description="稅率")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class TaxTypeResponse(TaxTypeBase):
    """稅別回應模型"""

    id: int = Field(description="稅別 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 單位模型
# ==========================================
class UnitBase(BaseModel):
    """單位基礎模型"""

    code: str = Field(max_length=10, description="單位代碼")
    name: str = Field(max_length=20, description="單位名稱")
    is_active: bool = Field(default=True, description="是否啟用")


class UnitCreate(UnitBase):
    """單位建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "PCS",
                    "name": "個",
                    "is_active": True,
                }
            ]
        }
    }


class UnitUpdate(BaseModel):
    """單位更新模型"""

    code: Optional[str] = Field(default=None, max_length=10, description="單位代碼")
    name: Optional[str] = Field(default=None, max_length=20, description="單位名稱")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class UnitResponse(UnitBase):
    """單位回應模型"""

    id: int = Field(description="單位 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 類別模型
# ==========================================
class CategoryBase(BaseModel):
    """類別基礎模型"""

    code: str = Field(max_length=20, description="類別代碼")
    name: str = Field(max_length=50, description="類別名稱")
    parent_id: Optional[int] = Field(default=None, description="上層類別 ID")
    level: int = Field(default=1, ge=1, description="類別層級")
    sort_order: int = Field(default=0, description="排序順序")
    is_active: bool = Field(default=True, description="是否啟用")


class CategoryCreate(CategoryBase):
    """類別建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "FOOD",
                    "name": "食品",
                    "parent_id": None,
                    "level": 1,
                    "sort_order": 1,
                    "is_active": True,
                }
            ]
        }
    }


class CategoryUpdate(BaseModel):
    """類別更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="類別代碼")
    name: Optional[str] = Field(default=None, max_length=50, description="類別名稱")
    parent_id: Optional[int] = Field(default=None, description="上層類別 ID")
    level: Optional[int] = Field(default=None, ge=1, description="類別層級")
    sort_order: Optional[int] = Field(default=None, description="排序順序")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class CategoryResponse(CategoryBase):
    """類別回應模型"""

    id: int = Field(description="類別 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 商品模型
# ==========================================
class ProductBase(BaseModel):
    """商品基礎模型"""

    code: str = Field(max_length=20, description="商品代碼")
    barcode: Optional[str] = Field(default=None, max_length=50, description="商品條碼")
    name: str = Field(max_length=100, description="商品名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="商品描述")
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="成本價")
    selling_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="售價")
    min_stock: int = Field(default=0, ge=0, description="最低庫存量")
    max_stock: int = Field(default=0, ge=0, description="最高庫存量")
    is_active: bool = Field(default=True, description="是否上架")
    category_id: Optional[int] = Field(default=None, description="類別 ID")
    unit_id: Optional[int] = Field(default=None, description="單位 ID")
    tax_type_id: Optional[int] = Field(default=None, description="稅別 ID")
    supplier_id: Optional[int] = Field(default=None, description="供應商 ID")


class ProductCreate(ProductBase):
    """商品建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "P001",
                    "barcode": "4710088123456",
                    "name": "可口可樂 350ml",
                    "description": "清涼解渴的碳酸飲料",
                    "cost_price": "15.00",
                    "selling_price": "25.00",
                    "min_stock": 10,
                    "max_stock": 100,
                    "is_active": True,
                    "category_id": 1,
                    "unit_id": 1,
                    "tax_type_id": 1,
                    "supplier_id": 1,
                }
            ]
        }
    }


class ProductUpdate(BaseModel):
    """商品更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="商品代碼")
    barcode: Optional[str] = Field(default=None, max_length=50, description="商品條碼")
    name: Optional[str] = Field(default=None, max_length=100, description="商品名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="商品描述")
    cost_price: Optional[Decimal] = Field(default=None, ge=0, description="成本價")
    selling_price: Optional[Decimal] = Field(default=None, ge=0, description="售價")
    min_stock: Optional[int] = Field(default=None, ge=0, description="最低庫存量")
    max_stock: Optional[int] = Field(default=None, ge=0, description="最高庫存量")
    is_active: Optional[bool] = Field(default=None, description="是否上架")
    category_id: Optional[int] = Field(default=None, description="類別 ID")
    unit_id: Optional[int] = Field(default=None, description="單位 ID")
    tax_type_id: Optional[int] = Field(default=None, description="稅別 ID")
    supplier_id: Optional[int] = Field(default=None, description="供應商 ID")


class ProductResponse(ProductBase):
    """商品回應模型"""

    id: int = Field(description="商品 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    category: Optional[CategoryResponse] = Field(default=None, description="類別資訊")
    unit: Optional[UnitResponse] = Field(default=None, description="單位資訊")
    tax_type: Optional[TaxTypeResponse] = Field(default=None, description="稅別資訊")

    model_config = {"from_attributes": True}
