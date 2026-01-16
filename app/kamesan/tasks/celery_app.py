"""
Celery 應用程式配置

建立並配置 Celery 實例，用於處理背景任務。

功能：
- 低庫存通知
- 報表產生
- 電子郵件發送
- 定期任務（盤點提醒等）
"""

from celery import Celery

from app.kamesan.core.config import settings

# ==========================================
# 建立 Celery 應用程式
# ==========================================
celery_app = Celery(
    "fastapi_demo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.kamesan.tasks.inventory_tasks",
        "app.kamesan.tasks.notification_tasks",
        "app.kamesan.tasks.report_tasks",
    ],
)

# ==========================================
# Celery 配置
# ==========================================
celery_app.conf.update(
    # 任務序列化格式
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 時區設定
    timezone="Asia/Taipei",
    enable_utc=True,
    # 任務執行設定
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 分鐘超時
    # 結果過期時間
    result_expires=3600,  # 1 小時
    # Worker 設定
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# ==========================================
# 定期任務設定（Celery Beat）
# ==========================================
celery_app.conf.beat_schedule = {
    # 每天早上 8 點檢查低庫存
    "check-low-stock-daily": {
        "task": "app.kamesan.tasks.inventory_tasks.check_low_stock",
        "schedule": 60 * 60 * 24,  # 每 24 小時
        # "schedule": crontab(hour=8, minute=0),  # 可使用 crontab
    },
    # 每週一產生週報
    "generate-weekly-report": {
        "task": "app.kamesan.tasks.report_tasks.generate_weekly_sales_report",
        "schedule": 60 * 60 * 24 * 7,  # 每 7 天
    },
    # 每 5 分鐘處理排程報表
    "process-scheduled-reports": {
        "task": "app.kamesan.tasks.report_tasks.process_scheduled_reports",
        "schedule": 60 * 5,  # 每 5 分鐘
    },
}
