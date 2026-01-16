"""
審計日誌服務

提供統一的審計日誌記錄功能。
"""

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.kamesan.models.audit_log import ActionType, AuditLog


async def create_audit_log(
    session: AsyncSession,
    action_type: ActionType,
    module: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    target_id: Optional[int] = None,
    target_name: Optional[str] = None,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None,
) -> AuditLog:
    """
    建立審計日誌

    參數：
        session: 資料庫連線
        action_type: 操作類型 (CREATE/UPDATE/DELETE/LOGIN/LOGOUT/VIEW/EXPORT)
        module: 操作模組 (如 users, products, orders)
        user_id: 操作者 ID
        username: 操作者帳號
        target_id: 目標資料 ID
        target_name: 目標資料名稱 (方便顯示)
        old_value: 修改前的值 (JSON)
        new_value: 修改後的值 (JSON)
        ip_address: 來源 IP
        user_agent: 瀏覽器資訊
        description: 操作說明

    回傳：
        建立的 AuditLog 物件
    """
    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        action_type=action_type,
        module=module,
        target_id=target_id,
        target_name=target_name,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description,
    )

    session.add(audit_log)
    # 注意：這裡不 commit，讓呼叫者決定何時 commit
    # 這樣可以確保審計日誌與主要操作在同一個交易中

    return audit_log


async def log_create(
    session: AsyncSession,
    module: str,
    target_id: int,
    target_name: str,
    new_value: Dict[str, Any],
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    description: Optional[str] = None,
) -> AuditLog:
    """記錄新增操作"""
    return await create_audit_log(
        session=session,
        action_type=ActionType.CREATE,
        module=module,
        user_id=user_id,
        username=username,
        target_id=target_id,
        target_name=target_name,
        new_value=new_value,
        ip_address=ip_address,
        description=description or f"新增 {module}: {target_name}",
    )


async def log_update(
    session: AsyncSession,
    module: str,
    target_id: int,
    target_name: str,
    old_value: Dict[str, Any],
    new_value: Dict[str, Any],
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    description: Optional[str] = None,
) -> AuditLog:
    """記錄更新操作"""
    return await create_audit_log(
        session=session,
        action_type=ActionType.UPDATE,
        module=module,
        user_id=user_id,
        username=username,
        target_id=target_id,
        target_name=target_name,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        description=description or f"更新 {module}: {target_name}",
    )


async def log_delete(
    session: AsyncSession,
    module: str,
    target_id: int,
    target_name: str,
    old_value: Dict[str, Any],
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    description: Optional[str] = None,
) -> AuditLog:
    """記錄刪除操作"""
    return await create_audit_log(
        session=session,
        action_type=ActionType.DELETE,
        module=module,
        user_id=user_id,
        username=username,
        target_id=target_id,
        target_name=target_name,
        old_value=old_value,
        ip_address=ip_address,
        description=description or f"刪除 {module}: {target_name}",
    )


async def log_login(
    session: AsyncSession,
    user_id: int,
    username: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
) -> AuditLog:
    """記錄登入操作"""
    description = f"使用者 {username} 登入" + ("成功" if success else "失敗")
    return await create_audit_log(
        session=session,
        action_type=ActionType.LOGIN,
        module="auth",
        user_id=user_id,
        username=username,
        target_id=user_id,
        target_name=username,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description,
    )


async def log_logout(
    session: AsyncSession,
    user_id: int,
    username: str,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """記錄登出操作"""
    return await create_audit_log(
        session=session,
        action_type=ActionType.LOGOUT,
        module="auth",
        user_id=user_id,
        username=username,
        target_id=user_id,
        target_name=username,
        ip_address=ip_address,
        description=f"使用者 {username} 登出",
    )
