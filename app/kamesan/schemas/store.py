"""
門市與倉庫相關 Schema 模型

定義門市和倉庫的請求和回應模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==========================================
# 倉庫模型
# ==========================================
class WarehouseBase(BaseModel):
    """倉庫基礎模型"""

    code: str = Field(max_length=20, description="倉庫代碼")
    name: str = Field(max_length=100, description="倉庫名稱")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    is_active: bool = Field(default=True, description="是否啟用")


class WarehouseCreate(WarehouseBase):
    """倉庫建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "WH001",
                    "name": "主倉庫",
                    "address": "台北市中正區某某路100號",
                    "is_active": True,
                }
            ]
        }
    }


class WarehouseUpdate(BaseModel):
    """倉庫更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="倉庫代碼")
    name: Optional[str] = Field(default=None, max_length=100, description="倉庫名稱")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class WarehouseResponse(WarehouseBase):
    """倉庫回應模型"""

    id: int = Field(description="倉庫 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 門市模型
# ==========================================
class StoreBase(BaseModel):
    """門市基礎模型"""

    code: str = Field(max_length=20, description="門市代碼")
    name: str = Field(max_length=100, description="門市名稱")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    is_active: bool = Field(default=True, description="是否營業中")
    warehouse_id: Optional[int] = Field(default=None, description="關聯倉庫 ID")


class StoreCreate(StoreBase):
    """門市建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "ST001",
                    "name": "台北旗艦店",
                    "address": "台北市信義區某某路50號",
                    "phone": "02-12345678",
                    "is_active": True,
                    "warehouse_id": 1,
                }
            ]
        }
    }


class StoreUpdate(BaseModel):
    """門市更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="門市代碼")
    name: Optional[str] = Field(default=None, max_length=100, description="門市名稱")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    is_active: Optional[bool] = Field(default=None, description="是否營業中")
    warehouse_id: Optional[int] = Field(default=None, description="關聯倉庫 ID")


class StoreResponse(StoreBase):
    """門市回應模型"""

    id: int = Field(description="門市 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    warehouse: Optional[WarehouseResponse] = Field(default=None, description="關聯倉庫資訊")

    model_config = {"from_attributes": True}
