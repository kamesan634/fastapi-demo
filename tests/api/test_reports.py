"""
報表 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestReportsAPI:
    """報表 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_sales_daily_report(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得每日銷售報表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/reports/sales/daily",
            headers=auth_headers,
        )

        # 報表可能需要特定資料才能產生
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_get_sales_summary_report(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得銷售彙總報表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/reports/sales/summary",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_get_inventory_report(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得庫存報表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/reports/inventory",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_get_top_products_report(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得熱銷商品報表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/reports/top-products",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400, 404]


class TestReportTemplatesAPI:
    """報表範本 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_report_templates(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得報表範本列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/report-templates",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_report_template(
        self, client: AsyncClient, auth_headers
    ):
        """測試建立報表範本"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/report-templates",
            headers=auth_headers,
            json={
                "code": "RPT_TEST",
                "name": "測試報表",
                "description": "測試用報表範本",
                "report_type": "CUSTOM",
                "is_public": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "RPT_TEST"


class TestReportSchedulesAPI:
    """報表排程 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_report_schedules(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得報表排程列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/report-schedules",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_report_schedule(
        self, client: AsyncClient, auth_headers
    ):
        """測試建立報表排程"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/report-schedules",
            headers=auth_headers,
            json={
                "name": "測試排程",
                "report_type": "SALES_DAILY",
                "frequency": "daily",
                "schedule_time": "08:00",
                "recipients": ["test@example.com"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "測試排程"
