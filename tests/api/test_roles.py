"""
角色 API 測試
"""

import pytest
from httpx import AsyncClient

from app.kamesan.core.config import settings


class TestRolesAPI:
    """角色 API 測試類別"""

    @pytest.mark.asyncio
    async def test_get_roles(self, client: AsyncClient, auth_headers, test_role):
        """測試取得角色列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/roles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_role(self, client: AsyncClient, auth_headers):
        """測試建立角色"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/roles",
            headers=auth_headers,
            json={
                "code": "NEW_ROLE",
                "name": "新角色",
                "description": "新建立的角色",
                "permissions": "test.read",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEW_ROLE"
        assert data["name"] == "新角色"

    @pytest.mark.asyncio
    async def test_create_role_duplicate_code(
        self, client: AsyncClient, auth_headers, test_role
    ):
        """測試建立角色 - 代碼重複"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/roles",
            headers=auth_headers,
            json={
                "code": test_role.code,
                "name": "重複角色",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_role_by_id(
        self, client: AsyncClient, auth_headers, test_role
    ):
        """測試取得單一角色"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/roles/{test_role.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_role.id
        assert data["code"] == test_role.code

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, client: AsyncClient, auth_headers):
        """測試取得不存在的角色"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/roles/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_role(
        self, client: AsyncClient, auth_headers, test_role
    ):
        """測試更新角色"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/roles/{test_role.id}",
            headers=auth_headers,
            json={
                "name": "更新後的角色",
                "permissions": "test.read,test.write,test.delete",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的角色"

    @pytest.mark.asyncio
    async def test_delete_role(
        self, client: AsyncClient, auth_headers, test_role
    ):
        """測試刪除角色"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/roles/{test_role.id}",
            headers=auth_headers,
        )

        # 如果有使用者使用此角色，可能會回傳 400
        assert response.status_code in [200, 400]
