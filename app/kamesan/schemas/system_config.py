"""
系統參數設定 Schema 模型

定義系統參數的請求和回應模型。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.system_config import ParamType


# ==========================================
# 系統參數模型
# ==========================================
class SystemParameterBase(BaseModel):
    """系統參數基礎模型"""

    param_code: str = Field(max_length=50, description="參數代碼")
    param_name: str = Field(max_length=100, description="參數名稱")
    param_category: str = Field(max_length=50, description="參數分類")
    param_type: ParamType = Field(default=ParamType.STRING, description="參數類型")
    param_value: str = Field(max_length=500, description="參數值")
    default_value: Optional[str] = Field(
        default=None, max_length=500, description="預設值"
    )
    description: Optional[str] = Field(default=None, max_length=500, description="說明")
    is_editable: bool = Field(default=True, description="是否可編輯")
    is_active: bool = Field(default=True, description="是否啟用")


class SystemParameterCreate(SystemParameterBase):
    """系統參數建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "param_code": "TAX_RATE",
                    "param_name": "營業稅率",
                    "param_category": "TAX",
                    "param_type": "DECIMAL",
                    "param_value": "0.05",
                    "default_value": "0.05",
                    "description": "預設營業稅率 5%",
                    "is_editable": True,
                    "is_active": True,
                }
            ]
        }
    }


class SystemParameterUpdate(BaseModel):
    """系統參數更新模型"""

    param_name: Optional[str] = Field(
        default=None, max_length=100, description="參數名稱"
    )
    param_value: Optional[str] = Field(
        default=None, max_length=500, description="參數值"
    )
    description: Optional[str] = Field(default=None, max_length=500, description="說明")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class SystemParameterResponse(SystemParameterBase):
    """系統參數回應模型"""

    id: int = Field(description="參數 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    created_by: Optional[int] = Field(default=None, description="建立者 ID")
    updated_by: Optional[int] = Field(default=None, description="更新者 ID")

    model_config = {"from_attributes": True}


class SystemParameterCategoryResponse(BaseModel):
    """系統參數分類回應模型"""

    category: str = Field(description="分類代碼")
    parameters: List[SystemParameterResponse] = Field(description="參數列表")
