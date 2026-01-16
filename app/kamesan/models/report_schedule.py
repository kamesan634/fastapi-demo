"""
排程報表模型

定義報表排程和執行記錄的資料結構。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, TimestampMixin


class ScheduleFrequency(str, Enum):
    """排程頻率"""

    ONCE = "once"  # 單次
    DAILY = "daily"  # 每日
    WEEKLY = "weekly"  # 每週
    MONTHLY = "monthly"  # 每月
    QUARTERLY = "quarterly"  # 每季
    YEARLY = "yearly"  # 每年


class ExecutionStatus(str, Enum):
    """執行狀態"""

    PENDING = "pending"  # 待執行
    RUNNING = "running"  # 執行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


class ReportSchedule(TimestampMixin, AuditMixin, table=True):
    """
    報表排程

    定義報表的自動產生排程。

    屬性:
        id: 主鍵
        name: 排程名稱
        description: 說明
        report_type: 報表類型（對應 ReportType）
        template_id: 報表範本 ID（可選）
        frequency: 排程頻率
        schedule_time: 排程時間（HH:MM 格式）
        day_of_week: 週幾執行（0-6，0=週日）
        day_of_month: 每月幾號執行（1-31）
        parameters: 報表參數（JSON）
        recipients: 收件人列表（JSON）
        export_format: 匯出格式
        is_active: 是否啟用
        last_run_at: 最後執行時間
        next_run_at: 下次執行時間
        owner_id: 擁有者 ID
    """

    __tablename__ = "report_schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="排程名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="說明")

    # 報表設定
    report_type: str = Field(max_length=50, description="報表類型")
    template_id: Optional[int] = Field(default=None, description="報表範本 ID")

    # 排程設定
    frequency: ScheduleFrequency = Field(
        default=ScheduleFrequency.DAILY, description="排程頻率"
    )
    schedule_time: str = Field(
        default="08:00", max_length=5, description="排程時間 (HH:MM)"
    )
    day_of_week: Optional[int] = Field(
        default=None, ge=0, le=6, description="週幾執行 (0-6, 0=週日)"
    )
    day_of_month: Optional[int] = Field(
        default=None, ge=1, le=31, description="每月幾號執行"
    )

    # 報表參數
    parameters: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="報表參數"
    )

    # 通知設定
    recipients: Optional[list[str]] = Field(
        default=None, sa_column=Column(JSON), description="收件人 Email 列表"
    )
    export_format: str = Field(default="excel", max_length=20, description="匯出格式")

    # 狀態
    is_active: bool = Field(default=True, description="是否啟用")
    last_run_at: Optional[datetime] = Field(default=None, description="最後執行時間")
    next_run_at: Optional[datetime] = Field(default=None, description="下次執行時間")

    # 擁有者
    owner_id: int = Field(description="擁有者 ID")

    # 關聯
    executions: list["ReportExecution"] = Relationship(back_populates="schedule")


class ReportExecution(TimestampMixin, table=True):
    """
    報表執行記錄

    記錄每次報表排程的執行狀況。

    屬性:
        id: 主鍵
        schedule_id: 排程 ID
        status: 執行狀態
        started_at: 開始時間
        completed_at: 完成時間
        duration_seconds: 執行時間（秒）
        file_path: 產生的檔案路徑
        file_size: 檔案大小（bytes）
        error_message: 錯誤訊息
        parameters_used: 實際使用的參數
        triggered_by: 觸發方式（schedule/manual）
    """

    __tablename__ = "report_executions"

    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="report_schedules.id", description="排程 ID")

    # 執行狀態
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING, description="執行狀態"
    )
    started_at: Optional[datetime] = Field(default=None, description="開始時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")
    duration_seconds: Optional[float] = Field(default=None, description="執行時間（秒）")

    # 結果
    file_path: Optional[str] = Field(default=None, max_length=500, description="檔案路徑")
    file_size: Optional[int] = Field(default=None, description="檔案大小")
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")

    # 執行參數
    parameters_used: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="實際使用的參數"
    )
    triggered_by: str = Field(
        default="schedule", max_length=20, description="觸發方式"
    )

    # 關聯
    schedule: Optional[ReportSchedule] = Relationship(back_populates="executions")
