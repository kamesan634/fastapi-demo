"""
Celery 背景任務模組

包含所有非同步背景任務的定義。

任務類別：
- celery_app: Celery 應用程式實例
- inventory_tasks: 庫存相關任務
- notification_tasks: 通知相關任務
- report_tasks: 報表相關任務
"""

from app.kamesan.tasks.celery_app import celery_app

__all__ = ["celery_app"]
