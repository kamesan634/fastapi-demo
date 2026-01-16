"""
班次管理 Schema 模型

定義班次的請求和回應模型。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.kamesan.models.shift import ShiftStatus


# ==========================================
# 班次模型
# ==========================================
class ShiftBase(BaseModel):
    """班次基礎模型"""

    store_id: int = Field(description="門市 ID")
    pos_id: Optional[str] = Field(default=None, max_length=20, description="POS 機台編號")
    cashier_id: int = Field(description="收銀員 ID")
    shift_date: date = Field(description="班次日期")


class ShiftOpenRequest(BaseModel):
    """開班請求模型"""

    store_id: int = Field(description="門市 ID")
    pos_id: Optional[str] = Field(default=None, max_length=20, description="POS 機台編號")
    opening_cash: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="開班現金",
    )
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "store_id": 1,
                    "pos_id": "POS-001",
                    "opening_cash": "5000.00",
                    "notes": "早班開班",
                }
            ]
        }
    }


class ShiftCloseRequest(BaseModel):
    """關班請求模型"""

    actual_cash: Decimal = Field(ge=0, description="實際清點現金")
    difference_note: Optional[str] = Field(
        default=None, max_length=500, description="差異說明"
    )
    notes: Optional[str] = Field(default=None, max_length=500, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "actual_cash": "15500.00",
                    "difference_note": "",
                    "notes": "早班關班",
                }
            ]
        }
    }


class ShiftResponse(ShiftBase):
    """班次回應模型"""

    id: int = Field(description="班次 ID")
    start_time: datetime = Field(description="開班時間")
    end_time: Optional[datetime] = Field(default=None, description="關班時間")

    # 現金
    opening_cash: Decimal = Field(description="開班現金")
    expected_cash: Decimal = Field(description="預期現金")
    actual_cash: Decimal = Field(description="實際清點現金")
    cash_difference: Decimal = Field(description="現金差異")
    difference_note: Optional[str] = Field(default=None, description="差異說明")

    # 銷售統計
    total_sales: Decimal = Field(description="總銷售額")
    total_refunds: Decimal = Field(description="總退款金額")
    total_transactions: int = Field(description="總交易筆數")
    total_cash_sales: Decimal = Field(description="現金銷售額")
    total_card_sales: Decimal = Field(description="刷卡銷售額")
    total_other_sales: Decimal = Field(description="其他方式銷售額")

    # 狀態
    status: ShiftStatus = Field(description="班次狀態")
    approved_by: Optional[int] = Field(default=None, description="主管核准人 ID")
    notes: Optional[str] = Field(default=None, description="備註")

    # 時間戳
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    created_by: Optional[int] = Field(default=None, description="建立者 ID")
    updated_by: Optional[int] = Field(default=None, description="更新者 ID")

    model_config = {"from_attributes": True}


class ShiftReportResponse(BaseModel):
    """班次報表回應模型"""

    shift: ShiftResponse = Field(description="班次資訊")

    # 銷售明細
    sales_by_payment_method: dict = Field(
        default_factory=dict, description="各付款方式銷售額"
    )
    sales_by_category: dict = Field(default_factory=dict, description="各類別銷售額")

    # 現金清點明細
    cash_count_detail: Optional[dict] = Field(
        default=None, description="現金清點明細（各面額數量）"
    )


class ShiftSummary(BaseModel):
    """班次摘要（用於列表顯示）"""

    id: int = Field(description="班次 ID")
    store_id: int = Field(description="門市 ID")
    cashier_id: int = Field(description="收銀員 ID")
    shift_date: date = Field(description="班次日期")
    start_time: datetime = Field(description="開班時間")
    end_time: Optional[datetime] = Field(default=None, description="關班時間")
    status: ShiftStatus = Field(description="班次狀態")
    total_sales: Decimal = Field(description="總銷售額")
    total_transactions: int = Field(description="總交易筆數")
    cash_difference: Decimal = Field(description="現金差異")

    model_config = {"from_attributes": True}
