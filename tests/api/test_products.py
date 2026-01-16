"""
商品 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestProductsAPI:
    """商品 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_products(self, client: AsyncClient, auth_headers, test_product):
        """測試取得商品列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_product(
        self, client: AsyncClient, auth_headers,
        test_category, test_unit, test_tax_type, test_supplier
    ):
        """測試建立商品"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/products",
            headers=auth_headers,
            json={
                "code": "P002",
                "barcode": "4710000000002",
                "name": "新商品",
                "cost_price": "30.00",
                "selling_price": "60.00",
                "min_stock": 5,
                "max_stock": 50,
                "category_id": test_category.id,
                "unit_id": test_unit.id,
                "tax_type_id": test_tax_type.id,
                "supplier_id": test_supplier.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "P002"
        assert data["name"] == "新商品"

    @pytest.mark.asyncio
    async def test_create_product_duplicate_code(
        self, client: AsyncClient, auth_headers, test_product,
        test_category, test_unit, test_tax_type
    ):
        """測試建立商品 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/products",
            headers=auth_headers,
            json={
                "code": test_product.code,
                "name": "重複商品",
                "selling_price": "100.00",
                "category_id": test_category.id,
                "unit_id": test_unit.id,
                "tax_type_id": test_tax_type.id,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_product_by_id(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """測試取得單一商品"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products/{test_product.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert data["code"] == test_product.code

    @pytest.mark.asyncio
    async def test_get_product_by_barcode(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """測試用條碼查詢商品"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products/barcode/{test_product.barcode}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == test_product.barcode

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的商品"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_product(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """測試更新商品"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/products/{test_product.id}",
            headers=auth_headers,
            json={
                "name": "更新後的商品",
                "selling_price": "150.00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的商品"

    @pytest.mark.asyncio
    async def test_delete_product(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """測試刪除商品"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/products/{test_product.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_products(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """測試搜尋商品"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products",
            headers=auth_headers,
            params={"keyword": "測試"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_filter_products_by_category(
        self, client: AsyncClient, auth_headers, test_product, test_category
    ):
        """測試依類別篩選商品"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/products",
            headers=auth_headers,
            params={"category_id": test_category.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
