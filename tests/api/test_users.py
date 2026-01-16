"""
使用者管理 API 測試

測試使用者的 CRUD 操作。
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestUsersAPI:
    """使用者管理 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_users(self, client: AsyncClient, auth_headers, admin_user):
        """測試取得使用者列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_create_user(self, client: AsyncClient, auth_headers, test_role):
        """測試建立使用者"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users",
            headers=auth_headers,
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "新使用者",
                "phone": "0987654321",
                "is_active": True,
                "role_id": test_role.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "新使用者"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, client: AsyncClient, auth_headers, admin_user
    ):
        """測試建立使用者 - 帳號重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users",
            headers=auth_headers,
            json={
                "username": "admin",  # 已存在的帳號
                "email": "another@example.com",
                "password": "password123",
                "full_name": "另一個使用者",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "帳號已存在"

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self, client: AsyncClient, auth_headers, admin_user
    ):
        """測試取得單一使用者"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/{admin_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == admin_user.id
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的使用者"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "使用者不存在"

    @pytest.mark.asyncio
    async def test_update_user(
        self, client: AsyncClient, auth_headers, test_user
    ):
        """測試更新使用者"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            headers=auth_headers,
            json={
                "full_name": "更新後的名稱",
                "phone": "0911111111",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "更新後的名稱"
        assert data["phone"] == "0911111111"

    @pytest.mark.asyncio
    async def test_delete_user(
        self, client: AsyncClient, auth_headers, test_user
    ):
        """測試刪除使用者"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # 確認已被軟刪除
        get_response = await client.get(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_self(self, client: AsyncClient, auth_headers, admin_user):
        """測試刪除自己的帳號（應該失敗）"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/users/{admin_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "不能刪除自己的帳號"
