"""
訂單 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestOrdersAPI:
    """訂單 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_orders(self, client: AsyncClient, auth_headers, test_order):
        """測試取得訂單列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_order(
        self, client: AsyncClient, auth_headers,
        test_store, test_product, test_customer
    ):
        """測試建立訂單"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            json={
                "store_id": test_store.id,
                "customer_id": test_customer.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 2,
                        "unit_price": "100.00",
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "order_number" in data
        assert data["store_id"] == test_store.id

    @pytest.mark.asyncio
    async def test_get_order_by_id(
        self, client: AsyncClient, auth_headers, test_order
    ):
        """測試取得單一訂單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders/{test_order.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_order.id
        assert data["order_number"] == test_order.order_number

    @pytest.mark.asyncio
    async def test_get_order_by_number(
        self, client: AsyncClient, auth_headers, test_order
    ):
        """測試用訂單編號查詢"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders/number/{test_order.order_number}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["order_number"] == test_order.order_number

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的訂單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_orders_by_store(
        self, client: AsyncClient, auth_headers, test_order, test_store
    ):
        """測試依門市篩選訂單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            params={"store_id": test_store.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_filter_orders_by_status(
        self, client: AsyncClient, auth_headers, test_order
    ):
        """測試依狀態篩選訂單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            params={"status": "COMPLETED"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_filter_orders_by_customer(
        self, client: AsyncClient, auth_headers, test_order, test_customer
    ):
        """測試依客戶篩選訂單"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            params={"customer_id": test_customer.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_cancel_order(
        self, client: AsyncClient, auth_headers,
        test_store, test_product, test_customer
    ):
        """測試取消訂單"""
        # 先建立一筆訂單
        create_response = await client.post(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            json={
                "store_id": test_store.id,
                "customer_id": test_customer.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 1,
                        "unit_price": "100.00",
                    }
                ],
            },
        )

        if create_response.status_code == 201:
            order_id = create_response.json()["id"]

            # 取消訂單
            cancel_response = await client.post(
                f"{settings.API_V1_PREFIX}/orders/{order_id}/cancel",
                headers=auth_headers,
            )

            assert cancel_response.status_code in [200, 400]


class TestPaymentsAPI:
    """付款 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_order_payments(
        self, client: AsyncClient, auth_headers, test_order
    ):
        """測試取得訂單付款記錄"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/orders/{test_order.id}/payments",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_payment(
        self, client: AsyncClient, auth_headers,
        test_store, test_product, test_customer
    ):
        """測試建立付款"""
        # 先建立一筆訂單
        create_response = await client.post(
            f"{settings.API_V1_PREFIX}/orders",
            headers=auth_headers,
            json={
                "store_id": test_store.id,
                "items": [
                    {
                        "product_id": test_product.id,
                        "quantity": 1,
                        "unit_price": "100.00",
                    }
                ],
            },
        )

        if create_response.status_code == 201:
            order_id = create_response.json()["id"]
            total_amount = create_response.json()["total_amount"]

            # 建立付款
            payment_response = await client.post(
                f"{settings.API_V1_PREFIX}/orders/{order_id}/payments",
                headers=auth_headers,
                json={
                    "payment_method": "CASH",
                    "amount": total_amount,
                },
            )

            assert payment_response.status_code in [200, 201]
