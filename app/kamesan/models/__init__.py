"""
資料模型模組

使用 SQLModel 定義所有資料庫模型。
SQLModel 結合了 SQLAlchemy 和 Pydantic 的功能，
可同時用於資料庫 ORM 和 API 資料驗證。

模型分類：
- user: 使用者與角色
- store: 門市與倉庫
- customer: 客戶與客戶等級
- supplier: 供應商
- product: 商品、類別、單位、稅別
- inventory: 庫存
- order: 訂單與付款
- promotion: 促銷與優惠券
- purchase: 採購單、驗收單、退貨單、供應商報價
- stock: 盤點單、調撥單
"""

# 匯入所有模型，確保 SQLModel 能夠建立所有資料表
from app.kamesan.models.user import Role, User
from app.kamesan.models.store import Store, Warehouse
from app.kamesan.models.customer import Customer, CustomerLevel, PointsLog
from app.kamesan.models.supplier import Supplier
from app.kamesan.models.product import Category, Product, TaxType, Unit
from app.kamesan.models.inventory import Inventory, InventoryTransaction
from app.kamesan.models.order import (
    Order,
    OrderItem,
    Payment,
    PaymentMethodSetting,
    SalesReturn,
    SalesReturnItem,
)
from app.kamesan.models.promotion import Coupon, Promotion
from app.kamesan.models.purchase import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SupplierPrice,
)
from app.kamesan.models.stock import (
    StockCount,
    StockCountItem,
    StockTransfer,
    StockTransferItem,
)
from app.kamesan.models.settings import (
    NumberingRule,
    NumberingSequence,
)
from app.kamesan.models.variant import (
    ProductSpecification,
    ProductVariant,
)
from app.kamesan.models.pricing import (
    ProductPromoPrice,
    VolumePricing,
)
from app.kamesan.models.combo import (
    ProductCombo,
    ProductComboItem,
)
from app.kamesan.models.system_config import SystemParameter
from app.kamesan.models.audit_log import AuditLog, ActionType
from app.kamesan.models.shift import CashierShift, ShiftStatus
from app.kamesan.models.invoice import Invoice, InvoiceType, CarrierType
from app.kamesan.models.report_template import ReportTemplate, ReportType
from app.kamesan.models.report_schedule import (
    ReportSchedule,
    ReportExecution,
    ScheduleFrequency,
    ExecutionStatus,
)

__all__ = [
    # 使用者
    "User",
    "Role",
    # 門市
    "Store",
    "Warehouse",
    # 客戶
    "Customer",
    "CustomerLevel",
    "PointsLog",
    # 供應商
    "Supplier",
    # 商品
    "Product",
    "Category",
    "TaxType",
    "Unit",
    # 庫存
    "Inventory",
    "InventoryTransaction",
    # 訂單
    "Order",
    "OrderItem",
    "Payment",
    "PaymentMethodSetting",
    "SalesReturn",
    "SalesReturnItem",
    # 促銷
    "Promotion",
    "Coupon",
    # 採購
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseReceipt",
    "PurchaseReceiptItem",
    "PurchaseReturn",
    "PurchaseReturnItem",
    "SupplierPrice",
    # 盤點與調撥
    "StockCount",
    "StockCountItem",
    "StockTransfer",
    "StockTransferItem",
    # 系統設定
    "NumberingRule",
    "NumberingSequence",
    # 商品規格
    "ProductSpecification",
    "ProductVariant",
    # 價格管理
    "VolumePricing",
    "ProductPromoPrice",
    # 商品組合
    "ProductCombo",
    "ProductComboItem",
    # 系統參數
    "SystemParameter",
    # 操作日誌
    "AuditLog",
    "ActionType",
    # 班次管理
    "CashierShift",
    "ShiftStatus",
    # 發票管理
    "Invoice",
    "InvoiceType",
    "CarrierType",
    # 報表範本
    "ReportTemplate",
    "ReportType",
    # 排程報表
    "ReportSchedule",
    "ReportExecution",
    "ScheduleFrequency",
    "ExecutionStatus",
]
