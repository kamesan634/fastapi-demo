"""
商品標籤列印 Schema

定義商品標籤列印的請求與回應格式。
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LabelFormat(str, Enum):
    """標籤格式"""

    STANDARD = "STANDARD"  # 標準標籤（商品名、價格、條碼）
    PRICE_TAG = "PRICE_TAG"  # 價格標籤（大字價格）
    SHELF_LABEL = "SHELF_LABEL"  # 貨架標籤（含位置資訊）
    BARCODE_ONLY = "BARCODE_ONLY"  # 僅條碼


class LabelSize(str, Enum):
    """標籤尺寸"""

    SMALL = "SMALL"  # 小標籤 (30x20mm)
    MEDIUM = "MEDIUM"  # 中標籤 (50x30mm)
    LARGE = "LARGE"  # 大標籤 (70x50mm)
    CUSTOM = "CUSTOM"  # 自訂尺寸


class OutputFormat(str, Enum):
    """輸出格式"""

    HTML = "HTML"  # HTML 格式（瀏覽器列印）
    PDF = "PDF"  # PDF 格式
    ZPL = "ZPL"  # Zebra 標籤印表機格式
    JSON = "JSON"  # JSON 資料（供前端渲染）


# ==========================================
# 標籤列印請求 Schema
# ==========================================
class LabelPrintItem(BaseModel):
    """單一標籤列印項目"""

    product_id: int = Field(description="商品 ID")
    quantity: int = Field(default=1, ge=1, le=1000, description="列印數量")
    custom_price: Optional[Decimal] = Field(
        default=None, ge=0, description="自訂價格（覆蓋商品售價）"
    )


class LabelPrintRequest(BaseModel):
    """標籤列印請求"""

    items: List[LabelPrintItem] = Field(
        min_length=1, max_length=100, description="列印項目"
    )
    label_format: LabelFormat = Field(
        default=LabelFormat.STANDARD, description="標籤格式"
    )
    label_size: LabelSize = Field(default=LabelSize.MEDIUM, description="標籤尺寸")
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML, description="輸出格式"
    )
    include_barcode: bool = Field(default=True, description="是否包含條碼")
    include_price: bool = Field(default=True, description="是否包含價格")
    include_code: bool = Field(default=True, description="是否包含商品代碼")
    store_id: Optional[int] = Field(default=None, description="門市 ID（貨架標籤用）")


class LabelPrintByCategory(BaseModel):
    """依類別列印標籤"""

    category_id: int = Field(description="類別 ID")
    quantity_per_product: int = Field(
        default=1, ge=1, le=100, description="每個商品列印數量"
    )
    label_format: LabelFormat = Field(
        default=LabelFormat.STANDARD, description="標籤格式"
    )
    label_size: LabelSize = Field(default=LabelSize.MEDIUM, description="標籤尺寸")
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML, description="輸出格式"
    )
    include_inactive: bool = Field(default=False, description="是否包含未上架商品")


# ==========================================
# 標籤資料 Schema
# ==========================================
class LabelData(BaseModel):
    """單一標籤資料"""

    product_id: int
    product_code: str
    product_name: str
    barcode: Optional[str] = None
    price: Decimal
    unit_name: Optional[str] = None
    category_name: Optional[str] = None
    store_name: Optional[str] = None
    shelf_location: Optional[str] = None


class LabelPrintResponse(BaseModel):
    """標籤列印回應"""

    labels: List[LabelData] = Field(description="標籤資料列表")
    total_count: int = Field(description="標籤總數")
    label_format: LabelFormat
    label_size: LabelSize
    output_format: OutputFormat


class LabelPreviewResponse(BaseModel):
    """標籤預覽回應"""

    content: str = Field(description="預覽內容（HTML 或其他格式）")
    content_type: str = Field(description="內容類型")
    total_labels: int = Field(description="標籤總數")


# ==========================================
# 標籤範本 Schema
# ==========================================
class LabelTemplateBase(BaseModel):
    """標籤範本基礎"""

    name: str = Field(max_length=50, description="範本名稱")
    label_format: LabelFormat = Field(description="標籤格式")
    label_size: LabelSize = Field(description="標籤尺寸")
    width_mm: Optional[int] = Field(default=None, ge=10, le=200, description="寬度(mm)")
    height_mm: Optional[int] = Field(
        default=None, ge=10, le=200, description="高度(mm)"
    )
    template_content: Optional[str] = Field(
        default=None, max_length=5000, description="範本內容（HTML/ZPL）"
    )
    is_default: bool = Field(default=False, description="是否為預設範本")


class LabelTemplateCreate(LabelTemplateBase):
    """建立標籤範本"""

    pass


class LabelTemplateUpdate(BaseModel):
    """更新標籤範本"""

    name: Optional[str] = Field(default=None, max_length=50, description="範本名稱")
    width_mm: Optional[int] = Field(default=None, ge=10, le=200, description="寬度(mm)")
    height_mm: Optional[int] = Field(
        default=None, ge=10, le=200, description="高度(mm)"
    )
    template_content: Optional[str] = Field(
        default=None, max_length=5000, description="範本內容"
    )
    is_default: Optional[bool] = Field(default=None, description="是否為預設範本")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class LabelTemplateResponse(LabelTemplateBase):
    """標籤範本回應"""

    id: int
    is_active: bool

    model_config = {"from_attributes": True}
