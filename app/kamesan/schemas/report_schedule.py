"""
排程報表 Schema

定義排程報表相關的請求和回應結構。
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.kamesan.models.report_schedule import ExecutionStatus, ScheduleFrequency


# ==========================================
# 基礎 Schema
# ==========================================
class ReportScheduleBase(BaseModel):
    """排程報表基礎 Schema"""

    name: str = Field(..., min_length=1, max_length=100, description="排程名稱")
    description: Optional[str] = Field(None, max_length=500, description="說明")
    report_type: str = Field(..., max_length=50, description="報表類型")
    template_id: Optional[int] = Field(None, description="報表範本 ID")
    frequency: ScheduleFrequency = Field(
        default=ScheduleFrequency.DAILY, description="排程頻率"
    )
    schedule_time: str = Field(default="08:00", description="排程時間 (HH:MM)")
    day_of_week: Optional[int] = Field(
        None, ge=0, le=6, description="週幾執行 (0=週日)"
    )
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="每月幾號執行")
    parameters: Optional[dict[str, Any]] = Field(None, description="報表參數")
    recipients: Optional[list[str]] = Field(None, description="收件人 Email 列表")
    export_format: str = Field(default="excel", description="匯出格式")
    is_active: bool = Field(default=True, description="是否啟用")

    @field_validator("schedule_time")
    @classmethod
    def validate_schedule_time(cls, v: str) -> str:
        """驗證時間格式"""
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, AttributeError):
            raise ValueError("時間格式必須為 HH:MM")

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """驗證收件人 Email"""
        if v is None:
            return v
        # 簡單驗證 Email 格式
        for email in v:
            if "@" not in email:
                raise ValueError(f"無效的 Email 格式: {email}")
        return v


# ==========================================
# 請求 Schema
# ==========================================
class ReportScheduleCreate(ReportScheduleBase):
    """建立排程報表請求"""

    pass


class ReportScheduleUpdate(BaseModel):
    """更新排程報表請求"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    report_type: Optional[str] = Field(None, max_length=50)
    template_id: Optional[int] = None
    frequency: Optional[ScheduleFrequency] = None
    schedule_time: Optional[str] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    parameters: Optional[dict[str, Any]] = None
    recipients: Optional[list[str]] = None
    export_format: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("schedule_time")
    @classmethod
    def validate_schedule_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, AttributeError):
            raise ValueError("時間格式必須為 HH:MM")


# ==========================================
# 回應 Schema
# ==========================================
class ReportScheduleSummary(BaseModel):
    """排程報表摘要回應"""

    id: int
    name: str
    report_type: str
    frequency: ScheduleFrequency
    schedule_time: str
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportScheduleResponse(ReportScheduleBase):
    """排程報表詳細回應"""

    id: int
    owner_id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportExecutionResponse(BaseModel):
    """報表執行記錄回應"""

    id: int
    schedule_id: int
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    parameters_used: Optional[dict[str, Any]] = None
    triggered_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# 執行請求 Schema
# ==========================================
class ExecuteScheduleRequest(BaseModel):
    """手動執行排程請求"""

    parameters: Optional[dict[str, Any]] = Field(None, description="覆寫參數")
    export_format: Optional[str] = Field(None, description="覆寫匯出格式")


# ==========================================
# 統計 Schema
# ==========================================
class ScheduleStatistics(BaseModel):
    """排程統計"""

    total_schedules: int = Field(..., description="排程總數")
    active_schedules: int = Field(..., description="啟用中排程數")
    total_executions: int = Field(..., description="執行總次數")
    success_count: int = Field(..., description="成功次數")
    failed_count: int = Field(..., description="失敗次數")
    success_rate: float = Field(..., description="成功率")
