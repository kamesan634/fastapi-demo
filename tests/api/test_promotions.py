"""
促銷與優惠券 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestPromotionsAPI:
    """促銷活動 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_promotions(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試取得促銷列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/promotions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_promotion(self, client: AsyncClient, auth_headers):
        """測試建立促銷活動"""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        response = await client.post(
            f"{settings.API_V1_PREFIX}/promotions",
            headers=auth_headers,
            json={
                "code": "PROMO002",
                "name": "新促銷活動",
                "description": "測試用促銷",
                "promotion_type": "PERCENTAGE",
                "discount_value": "15.00",
                "min_purchase": "200.00",
                "start_date": (now - timedelta(days=1)).isoformat(),
                "end_date": (now + timedelta(days=30)).isoformat(),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "PROMO002"
        assert data["name"] == "新促銷活動"

    @pytest.mark.asyncio
    async def test_create_promotion_duplicate_code(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試建立促銷 - 代碼重複"""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        response = await client.post(
            f"{settings.API_V1_PREFIX}/promotions",
            headers=auth_headers,
            json={
                "code": test_promotion.code,
                "name": "重複促銷",
                "promotion_type": "PERCENTAGE",
                "discount_value": "10.00",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=7)).isoformat(),
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_promotion_by_id(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試取得單一促銷"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/promotions/{test_promotion.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_promotion.id
        assert data["code"] == test_promotion.code

    @pytest.mark.asyncio
    async def test_get_promotion_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的促銷"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/promotions/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_promotion(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試更新促銷"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/promotions/{test_promotion.id}",
            headers=auth_headers,
            json={
                "name": "更新後的促銷",
                "discount_value": "20.00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的促銷"

    @pytest.mark.asyncio
    async def test_delete_promotion(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試刪除促銷"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/promotions/{test_promotion.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_active_promotions(
        self, client: AsyncClient, auth_headers, test_promotion
    ):
        """測試取得有效促銷"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/promotions",
            headers=auth_headers,
            params={"is_active": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestCouponsAPI:
    """優惠券 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_coupons(
        self, client: AsyncClient, auth_headers, test_coupon
    ):
        """測試取得優惠券列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/coupons",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_coupon(
        self, client: AsyncClient, auth_headers, test_customer
    ):
        """測試建立優惠券"""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        response = await client.post(
            f"{settings.API_V1_PREFIX}/coupons",
            headers=auth_headers,
            json={
                "code": "CPN002",
                "name": "新優惠券",
                "discount_type": "PERCENTAGE",
                "discount_value": "10.00",
                "min_purchase": "100.00",
                "start_date": (now - timedelta(days=1)).isoformat(),
                "end_date": (now + timedelta(days=30)).isoformat(),
                "customer_id": test_customer.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "CPN002"
        assert data["name"] == "新優惠券"

    @pytest.mark.asyncio
    async def test_create_coupon_duplicate_code(
        self, client: AsyncClient, auth_headers, test_coupon, test_customer
    ):
        """測試建立優惠券 - 代碼重複"""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        response = await client.post(
            f"{settings.API_V1_PREFIX}/coupons",
            headers=auth_headers,
            json={
                "code": test_coupon.code,
                "name": "重複優惠券",
                "discount_type": "FIXED_AMOUNT",
                "discount_value": "50.00",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=7)).isoformat(),
                "customer_id": test_customer.id,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_coupon_by_id(
        self, client: AsyncClient, auth_headers, test_coupon
    ):
        """測試取得單一優惠券"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/coupons/{test_coupon.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_coupon.id
        assert data["code"] == test_coupon.code

    @pytest.mark.asyncio
    async def test_get_coupon_by_code(
        self, client: AsyncClient, auth_headers, test_coupon
    ):
        """測試用代碼查詢優惠券"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/coupons/code/{test_coupon.code}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == test_coupon.code

    @pytest.mark.asyncio
    async def test_get_coupon_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的優惠券"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/coupons/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_customer_coupons(
        self, client: AsyncClient, auth_headers, test_coupon, test_customer
    ):
        """測試取得客戶的優惠券"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/coupons",
            headers=auth_headers,
            params={"customer_id": test_customer.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_delete_coupon(
        self, client: AsyncClient, auth_headers, test_coupon
    ):
        """測試刪除優惠券"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/coupons/{test_coupon.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
