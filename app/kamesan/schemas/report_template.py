"""
報表範本 Schema 模型

定義報表範本的請求和回應模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.kamesan.models.report_template import ReportType


# ==========================================
# 欄位設定模型
# ==========================================
class FieldConfig(BaseModel):
    """欄位設定"""

    name: str = Field(description="欄位名稱")
    label: str = Field(description="顯示標籤")
    visible: bool = Field(default=True, description="是否顯示")
    order: int = Field(default=0, description="排序順序")
    data_type: str = Field(default="string", description="資料類型")
    aggregation: Optional[str] = Field(
        default=None, description="聚合函數 (sum/avg/count/max/min)"
    )
    format: Optional[str] = Field(default=None, description="格式化字串")


class FilterConfig(BaseModel):
    """篩選設定"""

    field: str = Field(description="篩選欄位")
    operator: str = Field(description="運算子 (eq/ne/gt/gte/lt/lte/like/in)")
    value: Any = Field(description="篩選值")
    is_required: bool = Field(default=False, description="是否必填")


class SortConfig(BaseModel):
    """排序設定"""

    field: str = Field(description="排序欄位")
    direction: str = Field(default="asc", description="排序方向 (asc/desc)")


# ==========================================
# 報表範本模型
# ==========================================
class ReportTemplateBase(BaseModel):
    """報表範本基礎模型"""

    code: str = Field(max_length=50, description="報表代碼")
    name: str = Field(max_length=100, description="報表名稱")
    description: Optional[str] = Field(
        default=None, max_length=500, description="說明"
    )
    report_type: ReportType = Field(default=ReportType.CUSTOM, description="報表類型")
    is_public: bool = Field(default=False, description="是否公開")
    is_active: bool = Field(default=True, description="是否啟用")


class ReportTemplateCreate(ReportTemplateBase):
    """報表範本建立模型"""

    fields_config: Optional[List[FieldConfig]] = Field(
        default=None, description="欄位設定"
    )
    filters_config: Optional[List[FilterConfig]] = Field(
        default=None, description="篩選設定"
    )
    sort_config: Optional[List[SortConfig]] = Field(default=None, description="排序設定")
    format_config: Optional[Dict[str, Any]] = Field(
        default=None, description="格式設定"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "DAILY_SALES_BY_STORE",
                    "name": "門市每日銷售報表",
                    "description": "依門市統計每日銷售額",
                    "report_type": "SALES_DAILY",
                    "fields_config": [
                        {
                            "name": "store_name",
                            "label": "門市",
                            "visible": True,
                            "order": 1,
                        },
                        {
                            "name": "total_sales",
                            "label": "銷售額",
                            "visible": True,
                            "order": 2,
                            "aggregation": "sum",
                            "format": "currency",
                        },
                    ],
                    "is_public": True,
                    "is_active": True,
                }
            ]
        }
    }


class ReportTemplateUpdate(BaseModel):
    """報表範本更新模型"""

    name: Optional[str] = Field(default=None, max_length=100, description="報表名稱")
    description: Optional[str] = Field(
        default=None, max_length=500, description="說明"
    )
    fields_config: Optional[List[FieldConfig]] = Field(
        default=None, description="欄位設定"
    )
    filters_config: Optional[List[FilterConfig]] = Field(
        default=None, description="篩選設定"
    )
    sort_config: Optional[List[SortConfig]] = Field(default=None, description="排序設定")
    format_config: Optional[Dict[str, Any]] = Field(
        default=None, description="格式設定"
    )
    is_public: Optional[bool] = Field(default=None, description="是否公開")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class ReportTemplateResponse(ReportTemplateBase):
    """報表範本回應模型"""

    id: int = Field(description="範本 ID")
    fields_config: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="欄位設定"
    )
    filters_config: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="篩選設定"
    )
    sort_config: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="排序設定"
    )
    format_config: Optional[Dict[str, Any]] = Field(
        default=None, description="格式設定"
    )
    owner_id: Optional[int] = Field(default=None, description="擁有者 ID")
    is_system: bool = Field(description="是否系統內建")

    # 時間戳
    created_at: datetime = Field(description="建立時間")
    updated_at: datetime = Field(description="更新時間")
    created_by: Optional[int] = Field(default=None, description="建立者 ID")
    updated_by: Optional[int] = Field(default=None, description="更新者 ID")

    model_config = {"from_attributes": True}


class ReportTemplateSummary(BaseModel):
    """報表範本摘要（用於列表顯示）"""

    id: int = Field(description="範本 ID")
    code: str = Field(description="報表代碼")
    name: str = Field(description="報表名稱")
    report_type: ReportType = Field(description="報表類型")
    is_public: bool = Field(description="是否公開")
    is_system: bool = Field(description="是否系統內建")
    is_active: bool = Field(description="是否啟用")
    owner_id: Optional[int] = Field(default=None, description="擁有者 ID")

    model_config = {"from_attributes": True}
