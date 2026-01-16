"""
基礎模型模組

定義所有模型共用的基礎類別與 Mixin。

功能：
- 時間戳記 Mixin
- 軟刪除 Mixin
- 通用基礎模型
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """
    時間戳記 Mixin

    自動記錄資料建立與更新時間。
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="建立時間",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        description="更新時間",
    )


class SoftDeleteMixin(SQLModel):
    """
    軟刪除 Mixin

    支援軟刪除功能，資料不會真正刪除，
    而是標記 is_deleted 為 True。
    """

    is_deleted: bool = Field(default=False, description="是否已刪除")
    deleted_at: Optional[datetime] = Field(default=None, description="刪除時間")

    def soft_delete(self) -> None:
        """執行軟刪除"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """復原軟刪除的資料"""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin(SQLModel):
    """
    審計 Mixin

    記錄資料的建立者與更新者。
    """

    created_by: Optional[int] = Field(default=None, description="建立者 ID")
    updated_by: Optional[int] = Field(default=None, description="更新者 ID")
