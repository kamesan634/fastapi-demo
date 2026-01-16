"""
庫存 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestInventoriesAPI:
    """庫存 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_inventories(
        self, client: AsyncClient, auth_headers, test_inventory
    ):
        """測試取得庫存列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/inventories",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_inventory_by_id(
        self, client: AsyncClient, auth_headers, test_inventory
    ):
        """測試取得單一庫存"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/inventories/{test_inventory.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_inventory.id

    @pytest.mark.asyncio
    async def test_filter_inventories_by_warehouse(
        self, client: AsyncClient, auth_headers, test_inventory, test_warehouse
    ):
        """測試依倉庫篩選庫存"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/inventories",
            headers=auth_headers,
            params={"warehouse_id": test_warehouse.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_filter_inventories_by_product(
        self, client: AsyncClient, auth_headers, test_inventory, test_product
    ):
        """測試依商品篩選庫存"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/inventories",
            headers=auth_headers,
            params={"product_id": test_product.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_get_low_stock_inventories(
        self, client: AsyncClient, auth_headers, test_inventory
    ):
        """測試取得低庫存列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/inventories/low-stock",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_adjust_inventory(
        self, client: AsyncClient, auth_headers, test_inventory
    ):
        """測試調整庫存"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/inventories/{test_inventory.id}/adjust",
            headers=auth_headers,
            json={
                "quantity": 10,
                "reason": "測試調整",
            },
        )

        assert response.status_code in [200, 400]


class TestStockTransfersAPI:
    """庫存調撥 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_stock_transfers(
        self, client: AsyncClient, auth_headers, test_stock_transfer
    ):
        """測試取得調撥列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stock-transfers",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_stock_transfer(
        self, client: AsyncClient, auth_headers,
        test_warehouse, test_warehouse2, test_product
    ):
        """測試建立調撥單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stock-transfers",
            headers=auth_headers,
            json={
                "source_warehouse_id": test_warehouse.id,
                "destination_warehouse_id": test_warehouse2.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 5,
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "transfer_number" in data

    @pytest.mark.asyncio
    async def test_get_stock_transfer_by_id(
        self, client: AsyncClient, auth_headers, test_stock_transfer
    ):
        """測試取得單一調撥單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stock-transfers/{test_stock_transfer.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_stock_transfer.id

    @pytest.mark.asyncio
    async def test_approve_stock_transfer(
        self, client: AsyncClient, auth_headers, test_stock_transfer
    ):
        """測試核准調撥單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stock-transfers/{test_stock_transfer.id}/approve",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_cancel_stock_transfer(
        self, client: AsyncClient, auth_headers, test_stock_transfer
    ):
        """測試取消調撥單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stock-transfers/{test_stock_transfer.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400]


class TestStockCountsAPI:
    """庫存盤點 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_stock_counts(self, client: AsyncClient, auth_headers):
        """測試取得盤點列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stock-counts",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_stock_count(
        self, client: AsyncClient, auth_headers, test_warehouse, test_product
    ):
        """測試建立盤點單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stock-counts",
            headers=auth_headers,
            json={
                "warehouse_id": test_warehouse.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "system_quantity": 100,
                        "actual_quantity": 98,
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "count_number" in data
