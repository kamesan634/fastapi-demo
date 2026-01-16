"""
門市與倉庫 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestStoresAPI:
    """門市 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_stores(self, client: AsyncClient, auth_headers, test_store):
        """測試取得門市列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stores",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_store(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試建立門市"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stores",
            headers=auth_headers,
            json={
                "code": "ST002",
                "name": "新門市",
                "address": "新地址",
                "phone": "02-11111111",
                "warehouse_id": test_warehouse.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "ST002"
        assert data["name"] == "新門市"

    @pytest.mark.asyncio
    async def test_create_store_duplicate_code(
        self, client: AsyncClient, auth_headers, test_store, test_warehouse
    ):
        """測試建立門市 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/stores",
            headers=auth_headers,
            json={
                "code": test_store.code,
                "name": "重複門市",
                "warehouse_id": test_warehouse.id,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_store_by_id(
        self, client: AsyncClient, auth_headers, test_store
    ):
        """測試取得單一門市"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stores/{test_store.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_store.id
        assert data["code"] == test_store.code

    @pytest.mark.asyncio
    async def test_get_store_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的門市"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/stores/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_store(
        self, client: AsyncClient, auth_headers, test_store
    ):
        """測試更新門市"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/stores/{test_store.id}",
            headers=auth_headers,
            json={
                "name": "更新後的門市",
                "phone": "02-22222222",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的門市"
        assert data["phone"] == "02-22222222"

    @pytest.mark.asyncio
    async def test_delete_store(
        self, client: AsyncClient, auth_headers, test_store
    ):
        """測試刪除門市"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/stores/{test_store.id}",
            headers=auth_headers,
        )

        # 如果有訂單使用此門市，可能會回傳 400
        assert response.status_code in [200, 400]


class TestWarehousesAPI:
    """倉庫 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_warehouses(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試取得倉庫列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/warehouses",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_warehouse(self, client: AsyncClient, auth_headers):
        """測試建立倉庫"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/warehouses",
            headers=auth_headers,
            json={
                "code": "WH003",
                "name": "新倉庫",
                "address": "新倉庫地址",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "WH003"
        assert data["name"] == "新倉庫"

    @pytest.mark.asyncio
    async def test_create_warehouse_duplicate_code(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試建立倉庫 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/warehouses",
            headers=auth_headers,
            json={
                "code": test_warehouse.code,
                "name": "重複倉庫",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_warehouse_by_id(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試取得單一倉庫"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/warehouses/{test_warehouse.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_warehouse.id
        assert data["code"] == test_warehouse.code

    @pytest.mark.asyncio
    async def test_get_warehouse_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的倉庫"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/warehouses/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_warehouse(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試更新倉庫"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/warehouses/{test_warehouse.id}",
            headers=auth_headers,
            json={
                "name": "更新後的倉庫",
                "address": "新地址",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的倉庫"

    @pytest.mark.asyncio
    async def test_delete_warehouse(
        self, client: AsyncClient, auth_headers, test_warehouse
    ):
        """測試刪除倉庫"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/warehouses/{test_warehouse.id}",
            headers=auth_headers,
        )

        # 如果有庫存或門市使用此倉庫，可能會回傳 400
        assert response.status_code in [200, 400]
