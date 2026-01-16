"""
認證 API 測試

測試登入、登出、Token 刷新等功能。
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestAuthAPI:
    """認證 API 測試類別"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, admin_user):
        """測試登入成功"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={
                "username": "admin",
                "password": "admin123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        """測試密碼錯誤"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={
                "username": "admin",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "帳號或密碼錯誤"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, client: AsyncClient):
        """測試使用者不存在"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={
                "username": "nonexistent",
                "password": "password",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "帳號或密碼錯誤"

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """測試取得當前使用者資訊"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["email"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """測試未認證存取"""
        response = await client.get(f"{settings.API_V1_PREFIX}/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, admin_user):
        """測試 Token 刷新"""
        # 先登入取得 Token
        login_response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={
                "username": "admin",
                "password": "admin123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # 刷新 Token
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        """測試變更密碼"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "admin123",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "密碼變更成功"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, auth_headers
    ):
        """測試變更密碼 - 目前密碼錯誤"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "目前密碼錯誤"

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, client: AsyncClient, auth_headers):
        """測試變更密碼 - 確認密碼不符"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "admin123",
                "new_password": "newpassword123",
                "new_password_confirm": "differentpassword",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "新密碼與確認密碼不符"
