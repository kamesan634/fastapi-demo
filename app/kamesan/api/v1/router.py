"""
API v1 路由彙整

將所有 API 端點彙整到單一路由器。
"""

from fastapi import APIRouter

from app.kamesan.api.v1.endpoints import (
    audit_logs,
    auth,
    categories,
    combos,
    coupons,
    customer_levels,
    customers,
    inventories,
    invoices,
    numbering_rules,
    orders,
    payment_methods,
    products,
    product_import,
    product_labels,
    product_variants,
    promotions,
    purchase_orders,
    purchase_receipts,
    purchase_returns,
    purchase_suggestions,
    reports,
    report_schedules,
    report_templates,
    roles,
    sales_returns,
    shifts,
    stock_counts,
    stock_transfers,
    stores,
    supplier_prices,
    suppliers,
    system_config,
    tax_types,
    units,
    users,
    volume_pricing,
    warehouses,
)

# ==========================================
# 建立主路由器
# ==========================================
api_router = APIRouter()

# ==========================================
# 註冊各模組路由
# ==========================================
# 認證模組
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["認證"],
)

# 使用者管理
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["使用者管理"],
)

# 角色管理
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["角色管理"],
)

# 門市管理
api_router.include_router(
    stores.router,
    prefix="/stores",
    tags=["門市管理"],
)

# 倉庫管理
api_router.include_router(
    warehouses.router,
    prefix="/warehouses",
    tags=["倉庫管理"],
)

# 客戶等級管理
api_router.include_router(
    customer_levels.router,
    prefix="/customer-levels",
    tags=["客戶等級管理"],
)

# 客戶管理
api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["客戶管理"],
)

# 供應商管理
api_router.include_router(
    suppliers.router,
    prefix="/suppliers",
    tags=["供應商管理"],
)

# 商品類別管理
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["商品類別管理"],
)

# 單位管理
api_router.include_router(
    units.router,
    prefix="/units",
    tags=["單位管理"],
)

# 稅別管理
api_router.include_router(
    tax_types.router,
    prefix="/tax-types",
    tags=["稅別管理"],
)

# 付款方式管理
api_router.include_router(
    payment_methods.router,
    prefix="/payment-methods",
    tags=["付款方式管理"],
)

# 編號規則管理
api_router.include_router(
    numbering_rules.router,
    prefix="/numbering-rules",
    tags=["編號規則管理"],
)

# 商品管理
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["商品管理"],
)

# 商品匯入匯出
api_router.include_router(
    product_import.router,
    prefix="",
    tags=["商品匯入匯出"],
)

# 商品規格管理
api_router.include_router(
    product_variants.router,
    prefix="",
    tags=["商品規格管理"],
)

# 價格管理（量販價、促銷價）
api_router.include_router(
    volume_pricing.router,
    prefix="",
    tags=["價格管理"],
)

# 商品組合/套餐管理
api_router.include_router(
    combos.router,
    prefix="/combos",
    tags=["商品組合管理"],
)

# 商品標籤列印
api_router.include_router(
    product_labels.router,
    prefix="",
    tags=["商品標籤列印"],
)

# 庫存管理
api_router.include_router(
    inventories.router,
    prefix="/inventories",
    tags=["庫存管理"],
)

# 訂單管理
api_router.include_router(
    orders.router,
    prefix="/orders",
    tags=["訂單管理"],
)

# 銷售退貨管理
api_router.include_router(
    sales_returns.router,
    prefix="/sales-returns",
    tags=["銷售退貨管理"],
)

# 促銷管理
api_router.include_router(
    promotions.router,
    prefix="/promotions",
    tags=["促銷管理"],
)

# 優惠券管理
api_router.include_router(
    coupons.router,
    prefix="/coupons",
    tags=["優惠券管理"],
)

# 供應商價格管理
api_router.include_router(
    supplier_prices.router,
    prefix="/supplier-prices",
    tags=["供應商價格管理"],
)

# 採購單管理
api_router.include_router(
    purchase_orders.router,
    prefix="/purchase-orders",
    tags=["採購單管理"],
)

# 驗收單管理
api_router.include_router(
    purchase_receipts.router,
    prefix="/purchase-receipts",
    tags=["驗收單管理"],
)

# 退貨單管理
api_router.include_router(
    purchase_returns.router,
    prefix="/purchase-returns",
    tags=["退貨單管理"],
)

# 採購建議
api_router.include_router(
    purchase_suggestions.router,
    prefix="/purchase-suggestions",
    tags=["採購建議"],
)

# 庫存盤點管理
api_router.include_router(
    stock_counts.router,
    prefix="/stock-counts",
    tags=["庫存盤點管理"],
)

# 庫存調撥管理
api_router.include_router(
    stock_transfers.router,
    prefix="/stock-transfers",
    tags=["庫存調撥管理"],
)

# 報表
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["報表"],
)

# 系統參數設定
api_router.include_router(
    system_config.router,
    prefix="/system-config",
    tags=["系統參數設定"],
)

# 操作日誌
api_router.include_router(
    audit_logs.router,
    prefix="/audit-logs",
    tags=["操作日誌"],
)

# 班次管理
api_router.include_router(
    shifts.router,
    prefix="/shifts",
    tags=["班次管理"],
)

# 發票管理
api_router.include_router(
    invoices.router,
    prefix="/invoices",
    tags=["發票管理"],
)

# 報表範本
api_router.include_router(
    report_templates.router,
    prefix="/report-templates",
    tags=["報表範本"],
)

# 排程報表
api_router.include_router(
    report_schedules.router,
    prefix="/report-schedules",
    tags=["排程報表"],
)
