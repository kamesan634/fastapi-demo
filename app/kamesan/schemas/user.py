"""
使用者相關 Schema 模型

定義使用者和角色的請求和回應模型。

模型：
- UserCreate/Update/Response: 使用者 CRUD 模型
- RoleCreate/Update/Response: 角色 CRUD 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ==========================================
# 角色模型
# ==========================================
class RoleBase(BaseModel):
    """角色基礎模型"""

    code: str = Field(max_length=20, description="角色代碼")
    name: str = Field(max_length=50, description="角色名稱")
    description: Optional[str] = Field(default=None, max_length=200, description="角色描述")
    permissions: Optional[str] = Field(default=None, max_length=1000, description="權限列表")
    is_active: bool = Field(default=True, description="是否啟用")


class RoleCreate(RoleBase):
    """角色建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "ADMIN",
                    "name": "系統管理員",
                    "description": "擁有系統所有權限",
                    "permissions": "user.read,user.write,role.read,role.write",
                    "is_active": True,
                }
            ]
        }
    }


class RoleUpdate(BaseModel):
    """角色更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="角色代碼")
    name: Optional[str] = Field(default=None, max_length=50, description="角色名稱")
    description: Optional[str] = Field(default=None, max_length=200, description="角色描述")
    permissions: Optional[str] = Field(default=None, max_length=1000, description="權限列表")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class RoleResponse(RoleBase):
    """角色回應模型"""

    id: int = Field(description="角色 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 使用者模型
# ==========================================
class UserBase(BaseModel):
    """使用者基礎模型"""

    username: str = Field(max_length=50, description="帳號")
    email: EmailStr = Field(description="電子郵件")
    full_name: str = Field(max_length=50, description="姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    is_active: bool = Field(default=True, description="是否啟用")
    role_id: Optional[int] = Field(default=None, description="角色 ID")
    store_id: Optional[int] = Field(default=None, description="所屬門市 ID")


class UserCreate(UserBase):
    """使用者建立模型"""

    password: str = Field(min_length=6, max_length=128, description="密碼")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "full_name": "新使用者",
                    "phone": "0912345678",
                    "password": "password123",
                    "is_active": True,
                    "role_id": 1,
                    "store_id": None,
                }
            ]
        }
    }


class UserUpdate(BaseModel):
    """使用者更新模型"""

    username: Optional[str] = Field(default=None, max_length=50, description="帳號")
    email: Optional[EmailStr] = Field(default=None, description="電子郵件")
    full_name: Optional[str] = Field(default=None, max_length=50, description="姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
    role_id: Optional[int] = Field(default=None, description="角色 ID")
    store_id: Optional[int] = Field(default=None, description="所屬門市 ID")


class UserResponse(BaseModel):
    """使用者回應模型"""

    id: int = Field(description="使用者 ID")
    username: str = Field(description="帳號")
    email: str = Field(description="電子郵件")
    full_name: str = Field(description="姓名")
    phone: Optional[str] = Field(description="電話")
    is_active: bool = Field(description="是否啟用")
    is_superuser: bool = Field(description="是否為超級管理員")
    role_id: Optional[int] = Field(description="角色 ID")
    store_id: Optional[int] = Field(description="所屬門市 ID")
    last_login: Optional[datetime] = Field(description="最後登入時間")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    role: Optional[RoleResponse] = Field(default=None, description="角色資訊")

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """資料庫中的使用者模型（含雜湊密碼）"""

    hashed_password: str = Field(description="雜湊密碼")
