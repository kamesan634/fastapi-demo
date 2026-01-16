"""
客戶相關 Schema 模型

定義客戶和客戶等級的請求和回應模型。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ==========================================
# 客戶等級模型
# ==========================================
class CustomerLevelBase(BaseModel):
    """客戶等級基礎模型"""

    code: str = Field(max_length=20, description="等級代碼")
    name: str = Field(max_length=50, description="等級名稱")
    discount_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=1, description="折扣率")
    min_spending: Decimal = Field(default=Decimal("0.00"), ge=0, description="升級最低消費")
    description: Optional[str] = Field(default=None, max_length=200, description="等級描述")
    is_active: bool = Field(default=True, description="是否啟用")


class CustomerLevelCreate(CustomerLevelBase):
    """客戶等級建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "VIP",
                    "name": "VIP會員",
                    "discount_rate": "0.10",
                    "min_spending": "10000.00",
                    "description": "消費滿10000升級為VIP",
                    "is_active": True,
                }
            ]
        }
    }


class CustomerLevelUpdate(BaseModel):
    """客戶等級更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="等級代碼")
    name: Optional[str] = Field(default=None, max_length=50, description="等級名稱")
    discount_rate: Optional[Decimal] = Field(default=None, ge=0, le=1, description="折扣率")
    min_spending: Optional[Decimal] = Field(default=None, ge=0, description="升級最低消費")
    description: Optional[str] = Field(default=None, max_length=200, description="等級描述")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class CustomerLevelResponse(CustomerLevelBase):
    """客戶等級回應模型"""

    id: int = Field(description="等級 ID")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    model_config = {"from_attributes": True}


# ==========================================
# 客戶模型
# ==========================================
class CustomerBase(BaseModel):
    """客戶基礎模型"""

    code: str = Field(max_length=20, description="會員編號")
    name: str = Field(max_length=50, description="姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    email: Optional[EmailStr] = Field(default=None, description="電子郵件")
    birthday: Optional[date] = Field(default=None, description="生日")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    level_id: Optional[int] = Field(default=None, description="客戶等級 ID")
    is_active: bool = Field(default=True, description="是否啟用")


class CustomerCreate(CustomerBase):
    """客戶建立模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "C001",
                    "name": "王小明",
                    "phone": "0912345678",
                    "email": "wang@example.com",
                    "birthday": "1990-01-15",
                    "address": "台北市大安區某某路10號",
                    "level_id": 1,
                    "is_active": True,
                }
            ]
        }
    }


class CustomerUpdate(BaseModel):
    """客戶更新模型"""

    code: Optional[str] = Field(default=None, max_length=20, description="會員編號")
    name: Optional[str] = Field(default=None, max_length=50, description="姓名")
    phone: Optional[str] = Field(default=None, max_length=20, description="電話")
    email: Optional[EmailStr] = Field(default=None, description="電子郵件")
    birthday: Optional[date] = Field(default=None, description="生日")
    address: Optional[str] = Field(default=None, max_length=200, description="地址")
    level_id: Optional[int] = Field(default=None, description="客戶等級 ID")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class CustomerResponse(CustomerBase):
    """客戶回應模型"""

    id: int = Field(description="客戶 ID")
    total_spending: Decimal = Field(description="累計消費金額")
    points: int = Field(description="累計點數")
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")

    # 關聯資料
    level: Optional[CustomerLevelResponse] = Field(default=None, description="客戶等級資訊")

    model_config = {"from_attributes": True}


# ==========================================
# 點數管理模型
# ==========================================
class PointsAdjustRequest(BaseModel):
    """點數調整請求模型"""

    type: str = Field(
        description="異動類型: BONUS(活動贈點), ADJUST(手動調整), EXPIRE(過期扣除)"
    )
    points: int = Field(description="異動點數（正數增加，負數減少）")
    description: Optional[str] = Field(
        default=None, max_length=200, description="異動說明"
    )
    expire_date: Optional[date] = Field(default=None, description="點數到期日")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "BONUS",
                    "points": 100,
                    "description": "生日贈點",
                    "expire_date": "2027-12-31",
                }
            ]
        }
    }


class PointsLogResponse(BaseModel):
    """點數異動記錄回應模型"""

    id: int = Field(description="記錄 ID")
    customer_id: int = Field(description="客戶 ID")
    type: str = Field(description="異動類型")
    points: int = Field(description="異動點數")
    balance: int = Field(description="異動後餘額")
    reference_type: Optional[str] = Field(default=None, description="參考單據類型")
    reference_id: Optional[int] = Field(default=None, description="參考單據 ID")
    description: Optional[str] = Field(default=None, description="異動說明")
    expire_date: Optional[date] = Field(default=None, description="點數到期日")
    created_at: datetime = Field(description="建立時間")
    created_by: Optional[int] = Field(default=None, description="建立者 ID")

    model_config = {"from_attributes": True}
