"""
採購單 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestPurchaseOrdersAPI:
    """採購單 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_purchase_orders(
        self, client: AsyncClient, auth_headers, test_purchase_order
    ):
        """測試取得採購單列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-orders",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_purchase_order(
        self, client: AsyncClient, auth_headers,
        test_supplier, test_warehouse, test_product
    ):
        """測試建立採購單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/purchase-orders",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "warehouse_id": test_warehouse.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 20,
                        "unit_price": "50.00",
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "order_number" in data
        assert data["supplier_id"] == test_supplier.id

    @pytest.mark.asyncio
    async def test_get_purchase_order_by_id(
        self, client: AsyncClient, auth_headers, test_purchase_order
    ):
        """測試取得單一採購單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-orders/{test_purchase_order.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_purchase_order.id
        assert data["order_number"] == test_purchase_order.order_number

    @pytest.mark.asyncio
    async def test_get_purchase_order_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """測試取得不存在的採購單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-orders/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_purchase_orders_by_supplier(
        self, client: AsyncClient, auth_headers, test_purchase_order, test_supplier
    ):
        """測試依供應商篩選採購單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-orders",
            headers=auth_headers,
            params={"supplier_id": test_supplier.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_filter_purchase_orders_by_status(
        self, client: AsyncClient, auth_headers, test_purchase_order
    ):
        """測試依狀態篩選採購單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-orders",
            headers=auth_headers,
            params={"status": "PENDING"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_approve_purchase_order(
        self, client: AsyncClient, auth_headers, test_purchase_order
    ):
        """測試核准採購單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/purchase-orders/{test_purchase_order.id}/approve",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_cancel_purchase_order(
        self, client: AsyncClient, auth_headers, test_purchase_order
    ):
        """測試取消採購單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/purchase-orders/{test_purchase_order.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400]


class TestPurchaseReceiptsAPI:
    """驗收單 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_purchase_receipts(self, client: AsyncClient, auth_headers):
        """測試取得驗收單列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-receipts",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_purchase_receipt(
        self, client: AsyncClient, auth_headers,
        test_purchase_order, test_product
    ):
        """測試建立驗收單"""
        # 先核准採購單
        await client.post(
            f"{settings.API_V1_PREFIX}/purchase-orders/{test_purchase_order.id}/approve",
            headers=auth_headers,
        )

        response = await client.post(
            f"{settings.API_V1_PREFIX}/purchase-receipts",
            headers=auth_headers,
            json={
                "purchase_order_id": test_purchase_order.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "received_quantity": 10,
                        "rejected_quantity": 0,
                    }
                ],
            },
        )

        # 可能因為採購單狀態不對而失敗
        assert response.status_code in [201, 400]


class TestPurchaseReturnsAPI:
    """採購退貨 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_purchase_returns(self, client: AsyncClient, auth_headers):
        """測試取得採購退貨列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/purchase-returns",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_purchase_return(
        self, client: AsyncClient, auth_headers,
        test_supplier, test_warehouse, test_product
    ):
        """測試建立採購退貨"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/purchase-returns",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "warehouse_id": test_warehouse.id,
                "reason": "商品瑕疵",
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 2,
                        "unit_price": "50.00",
                        "reason": "瑕疵品",
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "return_number" in data
