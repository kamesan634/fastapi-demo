"""
服務層單元測試

測試 NumberingService 和 audit_service 功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.kamesan.models.audit_log import ActionType, AuditLog
from app.kamesan.models.settings import (
    DateFormat,
    DocumentType,
    NumberingRule,
    NumberingSequence,
    ResetPeriod,
)
from app.kamesan.services.audit_service import (
    create_audit_log,
    log_create,
    log_delete,
    log_login,
    log_logout,
    log_update,
)
from app.kamesan.services.numbering import NumberingService


class TestNumberingServicePeriodKey:
    """編號服務 - 週期鍵值測試（不需要資料庫）"""

    def test_get_period_key_never_reset(self):
        """測試週期鍵值 - 永不重置"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.NONE, ResetPeriod.NEVER)
        assert period_key == "GLOBAL"

    def test_get_period_key_daily_reset(self):
        """測試週期鍵值 - 每日重置"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.NONE, ResetPeriod.DAILY)
        expected = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert period_key == expected

    def test_get_period_key_monthly_reset(self):
        """測試週期鍵值 - 每月重置"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.NONE, ResetPeriod.MONTHLY)
        expected = datetime.now(timezone.utc).strftime("%Y%m")
        assert period_key == expected

    def test_get_period_key_yearly_reset(self):
        """測試週期鍵值 - 每年重置"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.NONE, ResetPeriod.YEARLY)
        expected = datetime.now(timezone.utc).strftime("%Y")
        assert period_key == expected

    def test_get_period_key_with_yyyymmdd_format(self):
        """測試週期鍵值 - YYYYMMDD 格式"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.YYYYMMDD, ResetPeriod.DAILY)
        expected = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert period_key == expected

    def test_get_period_key_with_yyyymm_format(self):
        """測試週期鍵值 - YYYYMM 格式"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.YYYYMM, ResetPeriod.MONTHLY)
        expected = datetime.now(timezone.utc).strftime("%Y%m")
        assert period_key == expected

    def test_get_period_key_with_yyyy_format(self):
        """測試週期鍵值 - YYYY 格式"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        period_key = service._get_period_key(DateFormat.YYYY, ResetPeriod.YEARLY)
        expected = datetime.now(timezone.utc).strftime("%Y")
        assert period_key == expected


class TestNumberingServiceDatePart:
    """編號服務 - 日期部分測試（不需要資料庫）"""

    def test_get_date_part_yyyymmdd(self):
        """測試日期部分 - YYYYMMDD"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        date_part = service._get_date_part(DateFormat.YYYYMMDD)
        expected = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert date_part == expected

    def test_get_date_part_yyyymm(self):
        """測試日期部分 - YYYYMM"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        date_part = service._get_date_part(DateFormat.YYYYMM)
        expected = datetime.now(timezone.utc).strftime("%Y%m")
        assert date_part == expected

    def test_get_date_part_yyyy(self):
        """測試日期部分 - YYYY"""
        from datetime import datetime, timezone

        mock_session = MagicMock()
        service = NumberingService(mock_session)

        date_part = service._get_date_part(DateFormat.YYYY)
        expected = datetime.now(timezone.utc).strftime("%Y")
        assert date_part == expected

    def test_get_date_part_none(self):
        """測試日期部分 - 無"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        date_part = service._get_date_part(DateFormat.NONE)
        assert date_part == ""


class TestNumberingServiceDefaultNumber:
    """編號服務 - 預設編號測試（不需要資料庫）"""

    def test_generate_default_number_sales_order(self):
        """測試生成預設編號 - 銷售訂單"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        order_number = service._generate_default_number(DocumentType.SALES_ORDER)
        assert order_number.startswith("ORD")

    def test_generate_default_number_purchase_order(self):
        """測試生成預設編號 - 採購單"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        po_number = service._generate_default_number(DocumentType.PURCHASE_ORDER)
        assert po_number.startswith("PO")

    def test_generate_default_number_goods_receipt(self):
        """測試生成預設編號 - 驗收單"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        gr_number = service._generate_default_number(DocumentType.GOODS_RECEIPT)
        assert gr_number.startswith("GR")

    def test_generate_default_number_sales_return(self):
        """測試生成預設編號 - 銷售退貨"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        rtn_number = service._generate_default_number(DocumentType.SALES_RETURN)
        assert rtn_number.startswith("RTN")

    def test_generate_default_number_purchase_return(self):
        """測試生成預設編號 - 採購退貨"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        pr_number = service._generate_default_number(DocumentType.PURCHASE_RETURN)
        assert pr_number.startswith("PR")

    def test_generate_default_number_stock_count(self):
        """測試生成預設編號 - 盤點"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        sc_number = service._generate_default_number(DocumentType.STOCK_COUNT)
        assert sc_number.startswith("SC")

    def test_generate_default_number_stock_transfer(self):
        """測試生成預設編號 - 調撥"""
        mock_session = MagicMock()
        service = NumberingService(mock_session)

        st_number = service._generate_default_number(DocumentType.STOCK_TRANSFER)
        assert st_number.startswith("ST")


class TestAuditServiceWithMock:
    """審計日誌服務測試（使用 Mock）"""

    @pytest.mark.asyncio
    async def test_create_audit_log(self):
        """測試建立審計日誌"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await create_audit_log(
            session=mock_session,
            action_type=ActionType.CREATE,
            module="test",
            user_id=1,
            username="testuser",
            target_id=100,
            target_name="Test Item",
            new_value={"name": "Test", "value": 123},
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            description="測試建立審計日誌",
        )

        assert audit_log is not None
        assert audit_log.action_type == ActionType.CREATE
        assert audit_log.module == "test"
        assert audit_log.user_id == 1
        assert audit_log.username == "testuser"
        assert audit_log.target_id == 100
        assert audit_log.target_name == "Test Item"
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.description == "測試建立審計日誌"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_create(self):
        """測試記錄新增操作"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_create(
            session=mock_session,
            module="products",
            target_id=1,
            target_name="測試商品",
            new_value={"name": "測試商品", "price": 100},
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
        )

        assert audit_log.action_type == ActionType.CREATE
        assert audit_log.module == "products"
        assert "新增" in audit_log.description

    @pytest.mark.asyncio
    async def test_log_update(self):
        """測試記錄更新操作"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_update(
            session=mock_session,
            module="products",
            target_id=1,
            target_name="測試商品",
            old_value={"name": "舊名稱", "price": 100},
            new_value={"name": "新名稱", "price": 150},
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
        )

        assert audit_log.action_type == ActionType.UPDATE
        assert audit_log.module == "products"
        assert audit_log.old_value == {"name": "舊名稱", "price": 100}
        assert audit_log.new_value == {"name": "新名稱", "price": 150}
        assert "更新" in audit_log.description

    @pytest.mark.asyncio
    async def test_log_delete(self):
        """測試記錄刪除操作"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_delete(
            session=mock_session,
            module="products",
            target_id=1,
            target_name="測試商品",
            old_value={"name": "測試商品", "price": 100},
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
        )

        assert audit_log.action_type == ActionType.DELETE
        assert audit_log.module == "products"
        assert "刪除" in audit_log.description

    @pytest.mark.asyncio
    async def test_log_login_success(self):
        """測試記錄登入成功"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_login(
            session=mock_session,
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        assert audit_log.action_type == ActionType.LOGIN
        assert audit_log.module == "auth"
        assert "登入" in audit_log.description
        assert "成功" in audit_log.description

    @pytest.mark.asyncio
    async def test_log_login_failure(self):
        """測試記錄登入失敗"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_login(
            session=mock_session,
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
            success=False,
        )

        assert audit_log.action_type == ActionType.LOGIN
        assert "登入" in audit_log.description
        assert "失敗" in audit_log.description

    @pytest.mark.asyncio
    async def test_log_logout(self):
        """測試記錄登出操作"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await log_logout(
            session=mock_session,
            user_id=1,
            username="admin",
            ip_address="192.168.1.1",
        )

        assert audit_log.action_type == ActionType.LOGOUT
        assert audit_log.module == "auth"
        assert "登出" in audit_log.description

    @pytest.mark.asyncio
    async def test_create_audit_log_minimal(self):
        """測試建立審計日誌 - 最少參數"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        audit_log = await create_audit_log(
            session=mock_session,
            action_type=ActionType.VIEW,
            module="reports",
        )

        assert audit_log is not None
        assert audit_log.action_type == ActionType.VIEW
        assert audit_log.module == "reports"
        assert audit_log.user_id is None
        assert audit_log.target_id is None
