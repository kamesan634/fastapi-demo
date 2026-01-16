"""
系統參數設定模型

定義系統參數的資料模型。

模型：
- SystemParameter: 系統參數設定
"""

from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class ParamType(str, Enum):
    """參數類型"""

    STRING = "STRING"
    INT = "INT"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class SystemParameter(TimestampMixin, AuditMixin, table=True):
    """
    系統參數設定模型

    欄位：
    - id: 主鍵
    - param_code: 參數代碼（唯一）
    - param_name: 參數名稱
    - param_category: 參數分類
    - param_type: 參數類型
    - param_value: 參數值
    - default_value: 預設值
    - description: 說明
    - is_editable: 是否可編輯
    - is_active: 是否啟用
    """

    __tablename__ = "system_parameters"

    id: Optional[int] = Field(default=None, primary_key=True)
    param_code: str = Field(
        max_length=50,
        unique=True,
        index=True,
        description="參數代碼",
    )
    param_name: str = Field(max_length=100, description="參數名稱")
    param_category: str = Field(
        max_length=50,
        index=True,
        description="參數分類",
    )
    param_type: ParamType = Field(
        default=ParamType.STRING,
        description="參數類型",
    )
    param_value: str = Field(max_length=500, description="參數值")
    default_value: Optional[str] = Field(
        default=None,
        max_length=500,
        description="預設值",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="說明",
    )
    is_editable: bool = Field(default=True, description="是否可編輯")
    is_active: bool = Field(default=True, description="是否啟用")
