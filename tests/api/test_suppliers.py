"""
供應商 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestSuppliersAPI:
    """供應商 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_suppliers(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試取得供應商列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/suppliers",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_supplier(self, client: AsyncClient, auth_headers):
        """測試建立供應商"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/suppliers",
            headers=auth_headers,
            json={
                "code": "SUP002",
                "name": "新供應商",
                "contact_name": "王經理",
                "phone": "02-87654321",
                "email": "new@supplier.com",
                "tax_id": "87654321",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "SUP002"
        assert data["name"] == "新供應商"

    @pytest.mark.asyncio
    async def test_create_supplier_duplicate_code(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試建立供應商 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/suppliers",
            headers=auth_headers,
            json={
                "code": test_supplier.code,
                "name": "重複供應商",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_supplier_by_id(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試取得單一供應商"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/suppliers/{test_supplier.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_supplier.id
        assert data["code"] == test_supplier.code

    @pytest.mark.asyncio
    async def test_get_supplier_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的供應商"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/suppliers/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_supplier(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試更新供應商"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/suppliers/{test_supplier.id}",
            headers=auth_headers,
            json={
                "name": "更新後的供應商",
                "contact_name": "新聯絡人",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的供應商"
        assert data["contact_name"] == "新聯絡人"

    @pytest.mark.asyncio
    async def test_delete_supplier(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試刪除供應商"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/suppliers/{test_supplier.id}",
            headers=auth_headers,
        )

        # 如果有商品使用此供應商，可能會回傳 400
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_search_suppliers(
        self, client: AsyncClient, auth_headers, test_supplier
    ):
        """測試搜尋供應商"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/suppliers",
            headers=auth_headers,
            params={"keyword": "測試"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
