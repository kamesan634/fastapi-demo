"""
報表相關背景任務

提供各種報表產生的背景任務。

任務：
- generate_daily_sales_report: 產生每日銷售報表
- generate_weekly_sales_report: 產生週銷售報表
- generate_inventory_report: 產生庫存報表
"""

from datetime import datetime, timedelta, timezone

from app.kamesan.tasks.celery_app import celery_app


@celery_app.task(name="app.kamesan.tasks.report_tasks.generate_daily_sales_report")
def generate_daily_sales_report(date_str: str = None) -> dict:
    """
    產生每日銷售報表

    彙整指定日期的銷售數據，產生報表。

    參數:
        date_str: 日期字串 (YYYY-MM-DD)，預設為昨天

    回傳值:
        dict: 報表資料
    """
    if date_str is None:
        report_date = datetime.now(timezone.utc) - timedelta(days=1)
        date_str = report_date.strftime("%Y-%m-%d")

    print(f"產生 {date_str} 銷售報表...")

    # TODO: 實作實際的報表查詢
    # async def _generate():
    #     async with async_session() as session:
    #         statement = (
    #             select(
    #                 func.count(Order.id).label("order_count"),
    #                 func.sum(Order.total_amount).label("total_sales"),
    #             )
    #             .where(func.date(Order.order_date) == date_str)
    #             .where(Order.status == OrderStatus.COMPLETED)
    #         )
    #         result = await session.execute(statement)
    #         return result.first()
    #
    # data = asyncio.run(_generate())

    # 模擬報表資料
    report = {
        "date": date_str,
        "order_count": 0,
        "total_sales": 0,
        "average_order_value": 0,
        "top_products": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"報表產生完成: {report}")
    return report


@celery_app.task(name="app.kamesan.tasks.report_tasks.generate_weekly_sales_report")
def generate_weekly_sales_report() -> dict:
    """
    產生週銷售報表

    彙整過去一週的銷售數據，產生週報。

    回傳值:
        dict: 週報資料
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    print(f"產生週銷售報表 ({start_date.date()} ~ {end_date.date()})...")

    # TODO: 實作實際的週報查詢
    report = {
        "period": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        },
        "total_orders": 0,
        "total_sales": 0,
        "daily_breakdown": [],
        "top_products": [],
        "top_customers": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"週報產生完成")
    return report


@celery_app.task(name="app.kamesan.tasks.report_tasks.generate_inventory_report")
def generate_inventory_report(warehouse_id: int = None) -> dict:
    """
    產生庫存報表

    彙整庫存狀況，包含庫存總值、低庫存商品等。

    參數:
        warehouse_id: 倉庫 ID，None 表示全部倉庫

    回傳值:
        dict: 庫存報表資料
    """
    print(f"產生庫存報表 (倉庫: {warehouse_id or '全部'})...")

    # TODO: 實作實際的庫存報表查詢
    report = {
        "warehouse_id": warehouse_id,
        "total_products": 0,
        "total_quantity": 0,
        "total_value": 0,
        "low_stock_items": [],
        "out_of_stock_items": [],
        "overstock_items": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"庫存報表產生完成")
    return report


@celery_app.task(name="app.kamesan.tasks.report_tasks.execute_scheduled_report")
def execute_scheduled_report(execution_id: int) -> dict:
    """
    執行排程報表

    根據執行記錄 ID 執行對應的報表產生任務。

    參數:
        execution_id: 執行記錄 ID

    回傳值:
        dict: 執行結果
    """
    print(f"執行排程報表 (執行 ID: {execution_id})...")

    # TODO: 實作實際的報表執行
    # 1. 查詢 ReportExecution 記錄
    # 2. 根據關聯的 ReportSchedule 取得報表設定
    # 3. 依據 report_type 呼叫對應的報表產生函式
    # 4. 更新執行狀態和結果

    result = {
        "execution_id": execution_id,
        "status": "success",
        "message": "報表執行完成",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"排程報表執行完成: {result}")
    return result


@celery_app.task(name="app.kamesan.tasks.report_tasks.process_scheduled_reports")
def process_scheduled_reports() -> dict:
    """
    處理到期的排程報表

    掃描所有到期的排程報表並觸發執行。
    此任務應由 Celery Beat 定期呼叫。

    回傳值:
        dict: 處理結果
    """
    print("處理排程報表...")

    # TODO: 實作實際的排程處理
    # 1. 查詢所有 is_active=True 且 next_run_at <= now 的排程
    # 2. 為每個排程建立 ReportExecution 記錄
    # 3. 觸發 execute_scheduled_report 任務
    # 4. 更新排程的 next_run_at

    result = {
        "processed_count": 0,
        "triggered_count": 0,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"排程報表處理完成: {result}")
    return result
