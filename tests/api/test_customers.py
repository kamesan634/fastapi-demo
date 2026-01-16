"""
客戶 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestCustomersAPI:
    """客戶 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_customers(self, client: AsyncClient, auth_headers, test_customer):
        """測試取得客戶列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customers",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_customer(
        self, client: AsyncClient, auth_headers, test_customer_level
    ):
        """測試建立客戶"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/customers",
            headers=auth_headers,
            json={
                "code": "C002",
                "name": "新客戶",
                "phone": "0922222222",
                "email": "new@example.com",
                "level_id": test_customer_level.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "C002"
        assert data["name"] == "新客戶"

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_code(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試建立客戶 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/customers",
            headers=auth_headers,
            json={
                "code": test_customer.code,
                "name": "重複客戶",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_customer_by_id(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試取得單一客戶"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customers/{test_customer.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_customer.id
        assert data["code"] == test_customer.code

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的客戶"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customers/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_customer(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試更新客戶"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/customers/{test_customer.id}",
            headers=auth_headers,
            json={
                "name": "更新後的客戶",
                "phone": "0933333333",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的客戶"
        assert data["phone"] == "0933333333"

    @pytest.mark.asyncio
    async def test_delete_customer(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試刪除客戶"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/customers/{test_customer.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_customers(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試搜尋客戶"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customers",
            headers=auth_headers,
            params={"keyword": "測試"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_search_customer_by_phone(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試依電話搜尋客戶"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customers",
            headers=auth_headers,
            params={"phone": test_customer.phone},
        )

        assert response.status_code == 200


class TestCustomerLevelsAPI:
    """客戶等級 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_customer_levels(
        self, client: AsyncClient, auth_headers, test_customer_level
    ):
        """測試取得客戶等級列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customer-levels",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_customer_level(self, client: AsyncClient, auth_headers):
        """測試建立客戶等級"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/customer-levels",
            headers=auth_headers,
            json={
                "code": "VIP",
                "name": "VIP會員",
                "discount_rate": "0.10",
                "min_spending": "50000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "VIP"
        assert data["name"] == "VIP會員"

    @pytest.mark.asyncio
    async def test_get_customer_level_by_id(
        self, client: AsyncClient, auth_headers, test_customer_level
    ):
        """測試取得單一客戶等級"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/customer-levels/{test_customer_level.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_customer_level.id

    @pytest.mark.asyncio
    async def test_update_customer_level(
        self, client: AsyncClient, auth_headers, test_customer_level
    ):
        """測試更新客戶等級"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/customer-levels/{test_customer_level.id}",
            headers=auth_headers,
            json={
                "name": "更新後的等級",
                "discount_rate": "0.05",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的等級"

    @pytest.mark.asyncio
    async def test_delete_customer_level(
        self, client: AsyncClient, auth_headers, test_customer_level
    ):
        """測試刪除客戶等級"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/customer-levels/{test_customer_level.id}",
            headers=auth_headers,
        )

        # 如果有客戶使用此等級，可能會回傳 400
        assert response.status_code in [200, 400]
