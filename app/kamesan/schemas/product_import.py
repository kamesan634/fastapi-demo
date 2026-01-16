"""
商品匯入匯出 Schema

定義商品批次匯入匯出的請求與回應格式。
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ImportMode(str, Enum):
    """匯入模式"""

    INSERT = "insert"  # 僅新增
    UPDATE = "update"  # 僅更新
    UPSERT = "upsert"  # 新增或更新


class ExportFormat(str, Enum):
    """匯出格式"""

    CSV = "csv"
    EXCEL = "excel"


class ImportStatus(str, Enum):
    """匯入狀態"""

    PENDING = "pending"  # 待處理
    VALIDATING = "validating"  # 驗證中
    VALIDATED = "validated"  # 驗證完成
    IMPORTING = "importing"  # 匯入中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失敗


class ProductImportRow(BaseModel):
    """商品匯入單筆資料"""

    row_number: int = Field(description="列號")
    code: Optional[str] = Field(default=None, description="商品編號")
    name: str = Field(description="商品名稱")
    barcode: Optional[str] = Field(default=None, description="商品條碼")
    category_code: str = Field(description="分類代碼")
    unit_code: str = Field(description="計量單位")
    cost_price: Decimal = Field(ge=0, description="成本價")
    selling_price: Decimal = Field(ge=0, description="標準售價")
    member_price: Optional[Decimal] = Field(default=None, ge=0, description="會員價")
    min_stock: Optional[int] = Field(default=0, ge=0, description="安全庫存")
    supplier_code: Optional[str] = Field(default=None, description="供應商代碼")
    status: Optional[str] = Field(default="ACTIVE", description="狀態")


class ValidationError(BaseModel):
    """驗證錯誤"""

    row_number: int = Field(description="列號")
    field: str = Field(description="欄位名稱")
    error: str = Field(description="錯誤訊息")


class ProductImportPreview(BaseModel):
    """匯入預覽資料"""

    row_number: int
    code: Optional[str]
    name: str
    category_code: str
    unit_code: str
    cost_price: Decimal
    selling_price: Decimal
    action: str = Field(description="操作類型（新增/更新）")
    has_error: bool = Field(default=False, description="是否有錯誤")
    errors: List[str] = Field(default=[], description="錯誤訊息")


class ImportValidationResult(BaseModel):
    """匯入驗證結果"""

    total_rows: int = Field(description="總資料列數")
    valid_rows: int = Field(description="有效列數")
    error_rows: int = Field(description="錯誤列數")
    insert_count: int = Field(description="將新增數量")
    update_count: int = Field(description="將更新數量")
    skip_count: int = Field(description="將跳過數量")
    errors: List[ValidationError] = Field(default=[], description="錯誤列表")
    preview: List[ProductImportPreview] = Field(default=[], description="預覽資料")


class ImportRequest(BaseModel):
    """匯入請求"""

    mode: ImportMode = Field(default=ImportMode.UPSERT, description="匯入模式")
    skip_errors: bool = Field(default=False, description="是否跳過錯誤資料")
    auto_generate_code: bool = Field(
        default=True, description="是否自動產生商品編號"
    )


class ImportResult(BaseModel):
    """匯入結果"""

    status: ImportStatus = Field(description="匯入狀態")
    total_rows: int = Field(description="總資料列數")
    success_count: int = Field(description="成功數量")
    insert_count: int = Field(description="新增數量")
    update_count: int = Field(description="更新數量")
    failed_count: int = Field(description="失敗數量")
    skip_count: int = Field(description="跳過數量")
    errors: List[ValidationError] = Field(default=[], description="錯誤列表")
    message: str = Field(description="結果訊息")


class ExportRequest(BaseModel):
    """匯出請求"""

    format: ExportFormat = Field(default=ExportFormat.CSV, description="匯出格式")
    category_ids: Optional[List[int]] = Field(default=None, description="分類 ID 過濾")
    supplier_ids: Optional[List[int]] = Field(default=None, description="供應商 ID 過濾")
    status: Optional[str] = Field(default=None, description="狀態過濾")
    include_inactive: bool = Field(default=False, description="是否包含停用商品")


class TemplateField(BaseModel):
    """範本欄位說明"""

    field_name: str = Field(description="欄位名稱")
    display_name: str = Field(description="顯示名稱")
    required: bool = Field(description="是否必填")
    data_type: str = Field(description="資料型態")
    description: str = Field(description="說明")
    example: str = Field(description="範例")


class ImportTemplateResponse(BaseModel):
    """匯入範本回應"""

    fields: List[TemplateField] = Field(description="欄位列表")
    notes: List[str] = Field(description="注意事項")
