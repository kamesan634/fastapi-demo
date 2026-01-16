"""
操作日誌 Schema 模型

定義操作日誌的請求和回應模型。
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.audit_log import ActionType


# ==========================================
# 操作日誌模型
# ==========================================
class AuditLogBase(BaseModel):
    """操作日誌基礎模型"""

    user_id: Optional[int] = Field(default=None, description="操作者 ID")
    username: Optional[str] = Field(default=None, max_length=50, description="操作者帳號")
    action_type: ActionType = Field(description="操作類型")
    module: str = Field(max_length=50, description="操作模組")
    target_id: Optional[int] = Field(default=None, description="目標資料 ID")
    target_name: Optional[str] = Field(
        default=None, max_length=200, description="目標資料名稱"
    )
    old_value: Optional[Dict[str, Any]] = Field(default=None, description="舊值")
    new_value: Optional[Dict[str, Any]] = Field(default=None, description="新值")
    ip_address: Optional[str] = Field(default=None, max_length=45, description="IP 位址")
    user_agent: Optional[str] = Field(
        default=None, max_length=500, description="瀏覽器資訊"
    )
    description: Optional[str] = Field(default=None, max_length=500, description="操作說明")


class AuditLogCreate(AuditLogBase):
    """操作日誌建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": 1,
                    "username": "admin",
                    "action_type": "CREATE",
                    "module": "users",
                    "target_id": 10,
                    "target_name": "新使用者",
                    "new_value": {"username": "test", "email": "test@example.com"},
                    "ip_address": "192.168.1.1",
                    "description": "建立新使用者",
                }
            ]
        }
    }


class AuditLogResponse(AuditLogBase):
    """操作日誌回應模型"""

    id: int = Field(description="日誌 ID")
    created_at: datetime = Field(description="建立時間")

    model_config = {"from_attributes": True}


class AuditLogQuery(BaseModel):
    """操作日誌查詢參數"""

    user_id: Optional[int] = Field(default=None, description="操作者 ID")
    action_type: Optional[ActionType] = Field(default=None, description="操作類型")
    module: Optional[str] = Field(default=None, description="操作模組")
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")


class AuditLogStatistics(BaseModel):
    """操作日誌統計"""

    total_count: int = Field(description="總筆數")
    action_counts: Dict[str, int] = Field(description="各操作類型筆數")
    module_counts: Dict[str, int] = Field(description="各模組筆數")
