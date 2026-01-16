"""
商品類別 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestCategoriesAPI:
    """商品類別 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient, auth_headers, test_category):
        """測試取得類別列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/categories",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, auth_headers):
        """測試建立類別"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/categories",
            headers=auth_headers,
            json={
                "code": "NEW_CAT",
                "name": "新類別",
                "level": 1,
                "sort_order": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEW_CAT"
        assert data["name"] == "新類別"

    @pytest.mark.asyncio
    async def test_create_category_duplicate_code(
        self, client: AsyncClient, auth_headers, test_category
    ):
        """測試建立類別 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/categories",
            headers=auth_headers,
            json={
                "code": test_category.code,
                "name": "重複類別",
                "level": 1,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_category_by_id(
        self, client: AsyncClient, auth_headers, test_category
    ):
        """測試取得單一類別"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/categories/{test_category.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_category.id
        assert data["code"] == test_category.code

    @pytest.mark.asyncio
    async def test_get_category_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的類別"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/categories/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_category(
        self, client: AsyncClient, auth_headers, test_category
    ):
        """測試更新類別"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/categories/{test_category.id}",
            headers=auth_headers,
            json={
                "name": "更新後的類別",
                "sort_order": 99,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的類別"
        assert data["sort_order"] == 99

    @pytest.mark.asyncio
    async def test_delete_category(
        self, client: AsyncClient, auth_headers, test_category
    ):
        """測試刪除類別"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/categories/{test_category.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """測試未認證存取"""
        response = await client.get(f"{settings.API_V1_PREFIX}/categories")
        assert response.status_code == 401
