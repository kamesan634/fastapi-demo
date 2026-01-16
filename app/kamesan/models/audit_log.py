"""
操作日誌模型

記錄系統所有操作的日誌。

模型：
- AuditLog: 操作日誌
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ActionType(str, Enum):
    """操作類型"""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW = "VIEW"
    EXPORT = "EXPORT"


class AuditLog(SQLModel, table=True):
    """
    操作日誌模型

    欄位：
    - id: 主鍵
    - user_id: 操作者 ID
    - username: 操作者帳號
    - action_type: 操作類型
    - module: 操作模組
    - target_id: 目標資料 ID
    - target_name: 目標資料名稱
    - old_value: 舊值 (JSON)
    - new_value: 新值 (JSON)
    - ip_address: IP 位址
    - user_agent: 瀏覽器資訊
    - description: 操作說明
    - created_at: 建立時間
    """

    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
        description="操作者 ID",
    )
    username: Optional[str] = Field(
        default=None,
        max_length=50,
        description="操作者帳號",
    )
    action_type: ActionType = Field(
        index=True,
        description="操作類型",
    )
    module: str = Field(
        max_length=50,
        index=True,
        description="操作模組",
    )
    target_id: Optional[int] = Field(
        default=None,
        description="目標資料 ID",
    )
    target_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="目標資料名稱",
    )
    old_value: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="舊值",
    )
    new_value: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="新值",
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP 位址",
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="瀏覽器資訊",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="操作說明",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="建立時間",
    )
