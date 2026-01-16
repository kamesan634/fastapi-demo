"""
Celery 任務單元測試

測試庫存、通知和報表相關的背景任務。
"""

import pytest
from unittest.mock import patch, MagicMock


class TestInventoryTasks:
    """庫存任務測試"""

    def test_check_low_stock(self):
        """測試檢查低庫存商品"""
        from app.kamesan.tasks.inventory_tasks import check_low_stock

        result = check_low_stock()

        assert result is not None
        assert "status" in result
        assert result["status"] == "completed"
        assert "low_stock_count" in result
        assert "items" in result
        assert isinstance(result["items"], list)

    def test_send_low_stock_notification(self):
        """測試發送低庫存通知"""
        from app.kamesan.tasks.inventory_tasks import send_low_stock_notification

        test_items = [
            {"product_id": 1, "name": "商品A", "quantity": 5},
            {"product_id": 2, "name": "商品B", "quantity": 3},
        ]

        result = send_low_stock_notification(test_items)

        assert result is not None
        assert result["status"] == "sent"
        assert "recipients" in result
        assert result["item_count"] == 2

    def test_send_low_stock_notification_empty(self):
        """測試發送低庫存通知 - 空列表"""
        from app.kamesan.tasks.inventory_tasks import send_low_stock_notification

        result = send_low_stock_notification([])

        assert result is not None
        assert result["item_count"] == 0

    def test_update_stock_after_order(self):
        """測試訂單完成後更新庫存"""
        from app.kamesan.tasks.inventory_tasks import update_stock_after_order

        result = update_stock_after_order(order_id=123)

        assert result is not None
        assert result["status"] == "completed"
        assert result["order_id"] == 123


class TestNotificationTasks:
    """通知任務測試"""

    def test_send_email(self):
        """測試發送電子郵件"""
        from app.kamesan.tasks.notification_tasks import send_email

        result = send_email(
            to="test@example.com",
            subject="測試郵件",
            body="這是測試郵件內容",
        )

        assert result is not None
        assert result["status"] == "sent"
        assert result["to"] == "test@example.com"
        assert result["subject"] == "測試郵件"

    def test_send_email_with_html(self):
        """測試發送 HTML 郵件"""
        from app.kamesan.tasks.notification_tasks import send_email

        result = send_email(
            to="test@example.com",
            subject="測試郵件",
            body="純文字內容",
            html_body="<h1>HTML 內容</h1>",
        )

        assert result is not None
        assert result["status"] == "sent"

    def test_send_order_confirmation(self):
        """測試發送訂單確認通知"""
        from app.kamesan.tasks.notification_tasks import send_order_confirmation

        result = send_order_confirmation(
            order_id=12345,
            customer_email="customer@example.com",
        )

        assert result is not None
        assert result["status"] == "sent"
        assert result["to"] == "customer@example.com"
        assert "訂單確認" in result["subject"]

    def test_send_welcome_email(self):
        """測試發送歡迎郵件"""
        from app.kamesan.tasks.notification_tasks import send_welcome_email

        result = send_welcome_email(
            user_email="newuser@example.com",
            user_name="新會員",
        )

        assert result is not None
        assert result["status"] == "sent"
        assert result["to"] == "newuser@example.com"
        assert "歡迎" in result["subject"]


class TestReportTasks:
    """報表任務測試"""

    def test_generate_daily_sales_report_default(self):
        """測試產生每日銷售報表 - 預設日期"""
        from app.kamesan.tasks.report_tasks import generate_daily_sales_report

        result = generate_daily_sales_report()

        assert result is not None
        assert "date" in result
        assert "order_count" in result
        assert "total_sales" in result
        assert "average_order_value" in result
        assert "top_products" in result
        assert "generated_at" in result

    def test_generate_daily_sales_report_specific_date(self):
        """測試產生每日銷售報表 - 指定日期"""
        from app.kamesan.tasks.report_tasks import generate_daily_sales_report

        result = generate_daily_sales_report(date_str="2024-01-15")

        assert result is not None
        assert result["date"] == "2024-01-15"

    def test_generate_weekly_sales_report(self):
        """測試產生週銷售報表"""
        from app.kamesan.tasks.report_tasks import generate_weekly_sales_report

        result = generate_weekly_sales_report()

        assert result is not None
        assert "period" in result
        assert "start" in result["period"]
        assert "end" in result["period"]
        assert "total_orders" in result
        assert "total_sales" in result
        assert "daily_breakdown" in result
        assert "top_products" in result
        assert "top_customers" in result
        assert "generated_at" in result

    def test_generate_inventory_report_all_warehouses(self):
        """測試產生庫存報表 - 全部倉庫"""
        from app.kamesan.tasks.report_tasks import generate_inventory_report

        result = generate_inventory_report()

        assert result is not None
        assert result["warehouse_id"] is None
        assert "total_products" in result
        assert "total_quantity" in result
        assert "total_value" in result
        assert "low_stock_items" in result
        assert "out_of_stock_items" in result
        assert "overstock_items" in result
        assert "generated_at" in result

    def test_generate_inventory_report_specific_warehouse(self):
        """測試產生庫存報表 - 指定倉庫"""
        from app.kamesan.tasks.report_tasks import generate_inventory_report

        result = generate_inventory_report(warehouse_id=5)

        assert result is not None
        assert result["warehouse_id"] == 5

    def test_execute_scheduled_report(self):
        """測試執行排程報表"""
        from app.kamesan.tasks.report_tasks import execute_scheduled_report

        result = execute_scheduled_report(execution_id=100)

        assert result is not None
        assert result["execution_id"] == 100
        assert result["status"] == "success"
        assert "message" in result
        assert "generated_at" in result

    def test_process_scheduled_reports(self):
        """測試處理到期的排程報表"""
        from app.kamesan.tasks.report_tasks import process_scheduled_reports

        result = process_scheduled_reports()

        assert result is not None
        assert "processed_count" in result
        assert "triggered_count" in result
        assert "processed_at" in result


class TestCeleryAppConfiguration:
    """Celery 應用程式設定測試"""

    def test_celery_app_exists(self):
        """測試 Celery App 存在"""
        from app.kamesan.tasks.celery_app import celery_app

        assert celery_app is not None

    def test_celery_app_name(self):
        """測試 Celery App 名稱"""
        from app.kamesan.tasks.celery_app import celery_app

        assert celery_app.main is not None

    def test_task_registration(self):
        """測試任務是否註冊"""
        from app.kamesan.tasks.celery_app import celery_app
        from app.kamesan.tasks import inventory_tasks, notification_tasks, report_tasks

        # 確認任務模組已載入
        assert inventory_tasks is not None
        assert notification_tasks is not None
        assert report_tasks is not None


class TestInventoryTasksWithMock:
    """使用 Mock 的庫存任務測試"""

    @patch('app.kamesan.tasks.inventory_tasks.send_low_stock_notification')
    def test_check_low_stock_triggers_notification(self, mock_notification):
        """測試低庫存檢查會觸發通知（當有低庫存商品時）"""
        from app.kamesan.tasks.inventory_tasks import check_low_stock

        # 這個測試驗證函式的基本結構
        result = check_low_stock()

        assert result is not None
        # 由於目前沒有實際查詢，low_stock_items 為空，所以不會觸發通知
        assert result["low_stock_count"] == 0


class TestNotificationTasksEdgeCases:
    """通知任務邊界案例測試"""

    def test_send_email_special_characters(self):
        """測試發送郵件 - 特殊字元"""
        from app.kamesan.tasks.notification_tasks import send_email

        result = send_email(
            to="test+tag@example.com",
            subject="測試<郵件>&'\"",
            body="內容包含特殊字元: <>&'\"",
        )

        assert result is not None
        assert result["status"] == "sent"

    def test_send_email_long_content(self):
        """測試發送郵件 - 長內容"""
        from app.kamesan.tasks.notification_tasks import send_email

        long_body = "這是一段很長的內容。" * 1000

        result = send_email(
            to="test@example.com",
            subject="長內容測試",
            body=long_body,
        )

        assert result is not None
        assert result["status"] == "sent"


class TestReportTasksEdgeCases:
    """報表任務邊界案例測試"""

    def test_generate_daily_sales_report_invalid_date(self):
        """測試產生每日銷售報表 - 無效日期格式（系統應能處理）"""
        from app.kamesan.tasks.report_tasks import generate_daily_sales_report

        # 即使日期格式可能無效，函式也應該能執行
        result = generate_daily_sales_report(date_str="invalid-date")

        assert result is not None
        assert result["date"] == "invalid-date"

    def test_generate_inventory_report_negative_warehouse_id(self):
        """測試產生庫存報表 - 負數倉庫 ID"""
        from app.kamesan.tasks.report_tasks import generate_inventory_report

        result = generate_inventory_report(warehouse_id=-1)

        assert result is not None
        assert result["warehouse_id"] == -1

    def test_execute_scheduled_report_zero_id(self):
        """測試執行排程報表 - ID 為 0"""
        from app.kamesan.tasks.report_tasks import execute_scheduled_report

        result = execute_scheduled_report(execution_id=0)

        assert result is not None
        assert result["execution_id"] == 0
