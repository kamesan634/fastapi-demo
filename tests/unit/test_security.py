"""
安全性模組單元測試

測試密碼雜湊和 JWT Token 功能。
"""

import pytest

from app.kamesan.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """密碼雜湊測試"""

    def test_password_hash(self):
        """測試密碼雜湊"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        # 雜湊後的密碼應該不同於原始密碼
        assert hashed != password
        # 雜湊後的密碼應該以 $2b$ 開頭（bcrypt）
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """測試正確密碼驗證"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """測試錯誤密碼驗證"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False


class TestJWTToken:
    """JWT Token 測試"""

    def test_create_access_token(self):
        """測試建立 Access Token"""
        token = create_access_token(subject="123")

        assert token is not None
        assert isinstance(token, str)
        # JWT Token 由三部分組成，以 . 分隔
        assert len(token.split(".")) == 3

    def test_create_refresh_token(self):
        """測試建立 Refresh Token"""
        token = create_refresh_token(subject="123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_access_token(self):
        """測試解碼 Access Token"""
        user_id = "123"
        token = create_access_token(subject=user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        """測試解碼 Refresh Token"""
        user_id = "123"
        token = create_refresh_token(subject=user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_verify_access_token(self):
        """測試驗證 Access Token"""
        user_id = "123"
        token = create_access_token(subject=user_id)
        verified_id = verify_token(token, token_type="access")

        assert verified_id == user_id

    def test_verify_refresh_token(self):
        """測試驗證 Refresh Token"""
        user_id = "123"
        token = create_refresh_token(subject=user_id)
        verified_id = verify_token(token, token_type="refresh")

        assert verified_id == user_id

    def test_verify_wrong_token_type(self):
        """測試驗證錯誤的 Token 類型"""
        token = create_access_token(subject="123")
        # 用 access token 驗證 refresh 類型
        verified_id = verify_token(token, token_type="refresh")

        assert verified_id is None

    def test_decode_invalid_token(self):
        """測試解碼無效 Token"""
        payload = decode_token("invalid.token.here")

        assert payload is None

    def test_create_token_with_additional_claims(self):
        """測試建立帶有額外 claims 的 Token"""
        token = create_access_token(
            subject="123",
            additional_claims={"role": "admin", "store_id": 1},
        )
        payload = decode_token(token)

        assert payload["role"] == "admin"
        assert payload["store_id"] == 1
