"""
編號規則相關 Schema 模型

定義編號規則的請求和回應模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.kamesan.models.settings import DateFormat, DocumentType, ResetPeriod


# ==========================================
# 編號規則模型
# ==========================================
class NumberingRuleBase(BaseModel):
    """編號規則基礎模型"""

    document_type: DocumentType = Field(description="單據類型")
    prefix: str = Field(min_length=1, max_length=10, description="前綴")
    date_format: DateFormat = Field(
        default=DateFormat.YYYYMMDD, description="日期格式"
    )
    sequence_digits: int = Field(
        default=4, ge=3, le=10, description="流水號位數"
    )
    reset_period: ResetPeriod = Field(
        default=ResetPeriod.DAILY, description="重置週期"
    )
    is_active: bool = Field(default=True, description="是否啟用")


class NumberingRuleCreate(NumberingRuleBase):
    """編號規則建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "document_type": "SALES_ORDER",
                    "prefix": "SO",
                    "date_format": "YYYYMMDD",
                    "sequence_digits": 4,
                    "reset_period": "DAILY",
                    "is_active": True,
                }
            ]
        }
    }


class NumberingRuleUpdate(BaseModel):
    """編號規則更新模型"""

    prefix: Optional[str] = Field(
        default=None, min_length=1, max_length=10, description="前綴"
    )
    date_format: Optional[DateFormat] = Field(
        default=None, description="日期格式"
    )
    sequence_digits: Optional[int] = Field(
        default=None, ge=3, le=10, description="流水號位數"
    )
    reset_period: Optional[ResetPeriod] = Field(
        default=None, description="重置週期"
    )
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class NumberingRuleResponse(NumberingRuleBase):
    """編號規則回應模型"""

    id: int = Field(description="規則 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


class NumberPreviewRequest(BaseModel):
    """編號預覽請求模型"""

    document_type: DocumentType = Field(description="單據類型")


class NumberPreviewResponse(BaseModel):
    """編號預覽回應模型"""

    document_type: DocumentType = Field(description="單據類型")
    sample_number: str = Field(description="範例編號")
    next_number: str = Field(description="下一個編號")
