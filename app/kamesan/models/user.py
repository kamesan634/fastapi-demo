"""
使用者與角色模型

定義系統使用者與角色的資料模型。

模型：
- Role: 角色（定義使用者權限群組）
- User: 使用者（系統登入帳號）
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.kamesan.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.kamesan.models.store import Store


class Role(TimestampMixin, table=True):
    """
    角色模型

    定義系統中的角色，每個角色可以有不同的權限。

    欄位：
    - id: 主鍵
    - code: 角色代碼（唯一）
    - name: 角色名稱
    - description: 角色描述
    - permissions: 權限列表（以逗號分隔的權限代碼）
    - is_active: 是否啟用

    關聯：
    - users: 此角色的所有使用者
    """

    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=20,
        unique=True,
        index=True,
        description="角色代碼",
    )
    name: str = Field(max_length=50, description="角色名稱")
    description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="角色描述",
    )
    permissions: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="權限列表（逗號分隔）",
    )
    is_active: bool = Field(default=True, description="是否啟用")

    # 關聯
    users: List["User"] = Relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.code}: {self.name}>"


class User(TimestampMixin, SoftDeleteMixin, AuditMixin, table=True):
    """
    使用者模型

    系統登入帳號，包含認證資訊與個人資料。

    欄位：
    - id: 主鍵
    - username: 帳號（唯一）
    - email: 電子郵件（唯一）
    - hashed_password: 雜湊後的密碼
    - full_name: 姓名
    - phone: 電話
    - is_active: 是否啟用
    - is_superuser: 是否為超級管理員
    - role_id: 角色 ID（外鍵）
    - store_id: 所屬門市 ID（外鍵）
    - last_login: 最後登入時間

    關聯：
    - role: 使用者的角色
    - store: 使用者所屬的門市
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(
        max_length=50,
        unique=True,
        index=True,
        description="帳號",
    )
    email: str = Field(
        max_length=100,
        unique=True,
        index=True,
        description="電子郵件",
    )
    hashed_password: str = Field(max_length=128, description="雜湊密碼")
    full_name: str = Field(max_length=50, description="姓名")
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="電話",
    )
    is_active: bool = Field(default=True, description="是否啟用")
    is_superuser: bool = Field(default=False, description="是否為超級管理員")
    last_login: Optional[datetime] = Field(default=None, description="最後登入時間")

    # 外鍵
    role_id: Optional[int] = Field(
        default=None,
        foreign_key="roles.id",
        description="角色 ID",
    )
    store_id: Optional[int] = Field(
        default=None,
        foreign_key="stores.id",
        description="所屬門市 ID",
    )

    # 關聯
    role: Optional[Role] = Relationship(back_populates="users")
    store: Optional["Store"] = Relationship(back_populates="users")

    def update_last_login(self) -> None:
        """更新最後登入時間"""
        self.last_login = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<User {self.username}>"
