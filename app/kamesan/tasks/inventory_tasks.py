"""
庫存相關背景任務

提供庫存檢查和處理的背景任務。

任務：
- check_low_stock: 檢查低庫存商品
- update_stock_after_order: 訂單完成後更新庫存
"""

import asyncio
from typing import List

from app.kamesan.tasks.celery_app import celery_app


@celery_app.task(name="app.kamesan.tasks.inventory_tasks.check_low_stock")
def check_low_stock() -> dict:
    """
    檢查低庫存商品

    掃描所有商品庫存，找出低於最低庫存量的商品，
    並發送通知給相關人員。

    回傳值:
        dict: 包含低庫存商品數量和列表
    """
    # 這裡使用同步方式，因為 Celery 任務預設是同步的
    # 如果需要非同步，可以使用 asyncio.run()

    print("開始檢查低庫存商品...")

    # 模擬檢查邏輯（實際應查詢資料庫）
    low_stock_items = []

    # TODO: 實作實際的資料庫查詢
    # async def _check():
    #     async with async_session() as session:
    #         statement = (
    #             select(Inventory, Product)
    #             .join(Product)
    #             .where(Inventory.quantity < Product.min_stock)
    #         )
    #         result = await session.execute(statement)
    #         return result.all()
    #
    # low_stock_items = asyncio.run(_check())

    result = {
        "status": "completed",
        "low_stock_count": len(low_stock_items),
        "items": low_stock_items,
    }

    print(f"檢查完成，發現 {len(low_stock_items)} 個低庫存商品")

    # 如果有低庫存商品，發送通知
    if low_stock_items:
        send_low_stock_notification.delay(low_stock_items)

    return result


@celery_app.task(name="app.kamesan.tasks.inventory_tasks.send_low_stock_notification")
def send_low_stock_notification(items: List[dict]) -> dict:
    """
    發送低庫存通知

    向相關人員發送低庫存警告通知。

    參數:
        items: 低庫存商品列表

    回傳值:
        dict: 通知發送結果
    """
    print(f"發送低庫存通知，共 {len(items)} 個商品...")

    # TODO: 實作實際的通知發送（Email、Line、Slack 等）
    # 這裡只是模擬

    return {
        "status": "sent",
        "recipients": ["manager@example.com", "warehouse@example.com"],
        "item_count": len(items),
    }


@celery_app.task(name="app.kamesan.tasks.inventory_tasks.update_stock_after_order")
def update_stock_after_order(order_id: int) -> dict:
    """
    訂單完成後更新庫存

    當訂單狀態變更為完成時，自動扣減相關商品的庫存。

    參數:
        order_id: 訂單 ID

    回傳值:
        dict: 庫存更新結果
    """
    print(f"處理訂單 {order_id} 的庫存扣減...")

    # TODO: 實作實際的庫存更新邏輯
    # async def _update():
    #     async with async_session() as session:
    #         # 查詢訂單明細
    #         # 扣減庫存
    #         # 建立異動記錄
    #         pass
    #
    # asyncio.run(_update())

    return {
        "status": "completed",
        "order_id": order_id,
    }
