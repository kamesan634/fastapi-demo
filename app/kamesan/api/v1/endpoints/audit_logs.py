"""
操作日誌 API 端點

提供操作日誌的查詢功能。
"""

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.audit_log import ActionType, AuditLog
from app.kamesan.schemas.audit_log import AuditLogResponse, AuditLogStatistics
from app.kamesan.schemas.common import PaginatedResponse

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="取得操作日誌列表",
)
async def get_audit_logs(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None, description="操作者 ID"),
    action_type: Optional[ActionType] = Query(default=None, description="操作類型"),
    module: Optional[str] = Query(default=None, description="操作模組"),
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
    search: Optional[str] = Query(default=None, description="搜尋關鍵字"),
):
    """
    取得操作日誌列表

    支援依操作者、操作類型、模組、日期範圍篩選。
    """
    statement = select(AuditLog)

    # 篩選條件
    if user_id:
        statement = statement.where(AuditLog.user_id == user_id)
    if action_type:
        statement = statement.where(AuditLog.action_type == action_type)
    if module:
        statement = statement.where(AuditLog.module == module)
    if start_date:
        start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        statement = statement.where(AuditLog.created_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        statement = statement.where(AuditLog.created_at <= end_datetime)
    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            (AuditLog.username.ilike(search_pattern))
            | (AuditLog.target_name.ilike(search_pattern))
            | (AuditLog.description.ilike(search_pattern))
        )

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序（最新的在前）
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(AuditLog.id.desc())

    result = await session.execute(statement)
    logs = result.scalars().all()

    return PaginatedResponse.create(items=logs, total=total, page=page, page_size=page_size)


@router.get(
    "/statistics",
    response_model=AuditLogStatistics,
    summary="取得操作日誌統計",
)
async def get_audit_log_statistics(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(default=None, description="開始日期"),
    end_date: Optional[date] = Query(default=None, description="結束日期"),
):
    """
    取得操作日誌統計

    統計各操作類型和模組的日誌數量。
    """
    statement = select(AuditLog)

    if start_date:
        start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        statement = statement.where(AuditLog.created_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        statement = statement.where(AuditLog.created_at <= end_datetime)

    result = await session.execute(statement)
    logs = result.scalars().all()

    # 統計
    action_counts: dict[str, int] = {}
    module_counts: dict[str, int] = {}

    for log in logs:
        action = log.action_type.value if log.action_type else "UNKNOWN"
        module = log.module or "UNKNOWN"

        action_counts[action] = action_counts.get(action, 0) + 1
        module_counts[module] = module_counts.get(module, 0) + 1

    return AuditLogStatistics(
        total_count=len(logs),
        action_counts=action_counts,
        module_counts=module_counts,
    )


@router.get(
    "/modules",
    response_model=list[str],
    summary="取得所有操作模組",
)
async def get_audit_log_modules(
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    取得所有有記錄的操作模組清單
    """
    statement = select(AuditLog.module).distinct()
    result = await session.execute(statement)
    modules = [row[0] for row in result.all() if row[0]]

    return sorted(modules)


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    summary="取得單一日誌",
)
async def get_audit_log(
    log_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    依 ID 取得單一操作日誌
    """
    statement = select(AuditLog).where(AuditLog.id == log_id)
    result = await session.execute(statement)
    log = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=404, detail="日誌不存在")

    return log
