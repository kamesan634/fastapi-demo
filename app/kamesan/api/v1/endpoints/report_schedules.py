"""
排程報表 API 端點

提供報表排程的 CRUD 和執行操作。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case
from sqlmodel import func, or_, select

from app.kamesan.core.deps import CurrentUser, SessionDep
from app.kamesan.models.report_schedule import (
    ExecutionStatus,
    ReportExecution,
    ReportSchedule,
    ScheduleFrequency,
)
from app.kamesan.schemas.common import PaginatedResponse
from app.kamesan.schemas.report_schedule import (
    ExecuteScheduleRequest,
    ReportExecutionResponse,
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleSummary,
    ReportScheduleUpdate,
    ScheduleStatistics,
)

router = APIRouter()


# ==========================================
# 輔助函式
# ==========================================
def calculate_next_run(schedule: ReportSchedule) -> datetime:
    """計算下次執行時間"""
    now = datetime.now(timezone.utc)
    hour, minute = map(int, schedule.schedule_time.split(":"))

    if schedule.frequency == ScheduleFrequency.ONCE:
        # 單次執行，如果已過時間則不設定
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            return None
        return next_run

    elif schedule.frequency == ScheduleFrequency.DAILY:
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    elif schedule.frequency == ScheduleFrequency.WEEKLY:
        days_ahead = schedule.day_of_week - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.hour * 60 + now.minute >= hour * 60 + minute):
            days_ahead += 7
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        next_run += timedelta(days=days_ahead)
        return next_run

    elif schedule.frequency == ScheduleFrequency.MONTHLY:
        day = schedule.day_of_month or 1
        next_run = now.replace(day=min(day, 28), hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            # 下個月
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)
        return next_run

    elif schedule.frequency == ScheduleFrequency.QUARTERLY:
        # 每季第一天
        quarter_months = [1, 4, 7, 10]
        current_quarter = (now.month - 1) // 3
        next_quarter_month = quarter_months[(current_quarter + 1) % 4]
        next_year = now.year if next_quarter_month > now.month else now.year + 1
        return datetime(next_year, next_quarter_month, 1, hour, minute, 0, tzinfo=timezone.utc)

    elif schedule.frequency == ScheduleFrequency.YEARLY:
        next_run = now.replace(month=1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run.replace(year=now.year + 1)
        return next_run

    return None


# ==========================================
# API 端點
# ==========================================
@router.get(
    "",
    response_model=PaginatedResponse[ReportScheduleSummary],
    summary="取得排程報表列表",
)
async def get_report_schedules(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    report_type: Optional[str] = Query(default=None, description="報表類型"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用"),
    frequency: Optional[ScheduleFrequency] = Query(default=None, description="排程頻率"),
    search: Optional[str] = Query(default=None, description="搜尋（名稱）"),
):
    """
    取得排程報表列表

    一般使用者只能看到自己的排程，管理員可以看到所有排程。
    """
    statement = select(ReportSchedule)

    # 權限過濾
    if not current_user.is_superuser:
        statement = statement.where(ReportSchedule.owner_id == current_user.id)

    # 篩選條件
    if report_type:
        statement = statement.where(ReportSchedule.report_type == report_type)
    if is_active is not None:
        statement = statement.where(ReportSchedule.is_active == is_active)
    if frequency:
        statement = statement.where(ReportSchedule.frequency == frequency)
    if search:
        statement = statement.where(ReportSchedule.name.ilike(f"%{search}%"))

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序（使用 case 來實現 NULLS LAST，因為 MySQL 不支援 nullslast()）
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(
        case((ReportSchedule.next_run_at.is_(None), 1), else_=0),
        ReportSchedule.next_run_at.asc(),
        ReportSchedule.name,
    )

    result = await session.execute(statement)
    schedules = result.scalars().all()

    return PaginatedResponse.create(
        items=schedules, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=ReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立排程報表",
)
async def create_report_schedule(
    schedule_data: ReportScheduleCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """建立新的排程報表"""
    schedule = ReportSchedule(
        name=schedule_data.name,
        description=schedule_data.description,
        report_type=schedule_data.report_type,
        template_id=schedule_data.template_id,
        frequency=schedule_data.frequency,
        schedule_time=schedule_data.schedule_time,
        day_of_week=schedule_data.day_of_week,
        day_of_month=schedule_data.day_of_month,
        parameters=schedule_data.parameters,
        recipients=schedule_data.recipients,
        export_format=schedule_data.export_format,
        is_active=schedule_data.is_active,
        owner_id=current_user.id,
        created_by=current_user.id,
    )

    # 計算下次執行時間
    schedule.next_run_at = calculate_next_run(schedule)

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return schedule


@router.get(
    "/statistics",
    response_model=ScheduleStatistics,
    summary="取得排程統計",
)
async def get_schedule_statistics(
    session: SessionDep,
    current_user: CurrentUser,
):
    """取得排程報表統計資料"""
    # 基礎查詢
    base_query = select(ReportSchedule)
    if not current_user.is_superuser:
        base_query = base_query.where(ReportSchedule.owner_id == current_user.id)

    # 排程總數
    total_result = await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_schedules = total_result.scalar() or 0

    # 啟用中排程
    active_query = base_query.where(ReportSchedule.is_active == True)
    active_result = await session.execute(
        select(func.count()).select_from(active_query.subquery())
    )
    active_schedules = active_result.scalar() or 0

    # 執行統計
    exec_base = select(ReportExecution).join(ReportSchedule)
    if not current_user.is_superuser:
        exec_base = exec_base.where(ReportSchedule.owner_id == current_user.id)

    total_exec_result = await session.execute(
        select(func.count()).select_from(exec_base.subquery())
    )
    total_executions = total_exec_result.scalar() or 0

    success_query = exec_base.where(ReportExecution.status == ExecutionStatus.SUCCESS)
    success_result = await session.execute(
        select(func.count()).select_from(success_query.subquery())
    )
    success_count = success_result.scalar() or 0

    failed_query = exec_base.where(ReportExecution.status == ExecutionStatus.FAILED)
    failed_result = await session.execute(
        select(func.count()).select_from(failed_query.subquery())
    )
    failed_count = failed_result.scalar() or 0

    success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0.0

    return ScheduleStatistics(
        total_schedules=total_schedules,
        active_schedules=active_schedules,
        total_executions=total_executions,
        success_count=success_count,
        failed_count=failed_count,
        success_rate=round(success_rate, 2),
    )


@router.get(
    "/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="取得單一排程",
)
async def get_report_schedule(
    schedule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """依 ID 取得排程詳情"""
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限存取此排程")

    return schedule


@router.put(
    "/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="更新排程",
)
async def update_report_schedule(
    schedule_id: int,
    schedule_data: ReportScheduleUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """更新排程報表設定"""
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限修改此排程")

    # 更新欄位
    update_data = schedule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    # 重新計算下次執行時間
    schedule.next_run_at = calculate_next_run(schedule)
    schedule.updated_by = current_user.id

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return schedule


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除排程",
)
async def delete_report_schedule(
    schedule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """刪除排程報表"""
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限刪除此排程")

    await session.delete(schedule)
    await session.commit()


@router.post(
    "/{schedule_id}/execute",
    response_model=ReportExecutionResponse,
    summary="手動執行排程",
)
async def execute_report_schedule(
    schedule_id: int,
    request: ExecuteScheduleRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    手動執行排程報表

    立即觸發報表產生，不等待排程時間。
    """
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限執行此排程")

    # 合併參數
    parameters = schedule.parameters or {}
    if request.parameters:
        parameters.update(request.parameters)

    # 建立執行記錄
    execution = ReportExecution(
        schedule_id=schedule_id,
        status=ExecutionStatus.PENDING,
        parameters_used=parameters,
        triggered_by="manual",
    )

    session.add(execution)
    await session.commit()
    await session.refresh(execution)

    # TODO: 觸發 Celery 任務
    # from app.kamesan.tasks.report_tasks import execute_scheduled_report
    # execute_scheduled_report.delay(execution.id)

    # 模擬立即執行（實際應該由 Celery 處理）
    execution.status = ExecutionStatus.RUNNING
    execution.started_at = datetime.now(timezone.utc)
    session.add(execution)
    await session.commit()
    await session.refresh(execution)

    return execution


@router.get(
    "/{schedule_id}/history",
    response_model=PaginatedResponse[ReportExecutionResponse],
    summary="取得執行歷史",
)
async def get_execution_history(
    schedule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[ExecutionStatus] = Query(default=None, description="執行狀態"),
):
    """取得排程報表的執行歷史記錄"""
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限存取此排程")

    statement = select(ReportExecution).where(ReportExecution.schedule_id == schedule_id)

    if status:
        statement = statement.where(ReportExecution.status == status)

    # 計算總數
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar() or 0

    # 分頁和排序
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(
        ReportExecution.created_at.desc()
    )

    result = await session.execute(statement)
    executions = result.scalars().all()

    return PaginatedResponse.create(
        items=executions, total=total, page=page, page_size=page_size
    )


@router.post(
    "/{schedule_id}/toggle",
    response_model=ReportScheduleResponse,
    summary="切換排程啟用狀態",
)
async def toggle_schedule_status(
    schedule_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    """切換排程的啟用/停用狀態"""
    schedule = await session.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")

    # 檢查權限
    if schedule.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="無權限修改此排程")

    schedule.is_active = not schedule.is_active

    # 重新計算下次執行時間
    if schedule.is_active:
        schedule.next_run_at = calculate_next_run(schedule)
    else:
        schedule.next_run_at = None

    schedule.updated_by = current_user.id

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return schedule
