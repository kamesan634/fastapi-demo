#!/usr/bin/env python
"""
Seed Data 腳本

建立測試用的初始資料，包含所有資料表的假資料。

使用方式:
    python scripts/seed_data.py

注意：
    執行前請確保資料庫已啟動且已執行 Alembic 遷移
"""

import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# 將專案根目錄加入 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.kamesan.core.config import settings
from app.kamesan.core.security import get_password_hash
from app.kamesan.models.audit_log import ActionType, AuditLog
from app.kamesan.models.customer import Customer, CustomerLevel, PointsLog, PointsLogType
from app.kamesan.models.inventory import Inventory, InventoryTransaction, TransactionType
from app.kamesan.models.invoice import CarrierType, Invoice, InvoiceType
from app.kamesan.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentMethodSetting,
    PaymentStatus,
    ReturnReason,
    SalesReturn,
    SalesReturnItem,
    SalesReturnStatus,
)
from app.kamesan.models.product import Category, Product, TaxType, Unit
from app.kamesan.models.promotion import Coupon, DiscountType, Promotion, PromotionType
from app.kamesan.models.purchase import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    PurchaseReceipt,
    PurchaseReceiptItem,
    PurchaseReceiptStatus,
    PurchaseReturn,
    PurchaseReturnItem,
    PurchaseReturnStatus,
    SupplierPrice,
)
from app.kamesan.models.report_schedule import (
    ExecutionStatus,
    ReportExecution,
    ReportSchedule,
    ScheduleFrequency,
)
from app.kamesan.models.report_template import ReportTemplate, ReportType
from app.kamesan.models.shift import CashierShift, ShiftStatus
from app.kamesan.models.stock import (
    StockCount,
    StockCountItem,
    StockCountStatus,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from app.kamesan.models.store import Store, Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.models.system_config import ParamType, SystemParameter
from app.kamesan.models.user import Role, User


async def create_roles(session: AsyncSession) -> dict:
    """建立角色"""
    print("建立角色...")
    roles_data = [
        {
            "code": "ADMIN",
            "name": "系統管理員",
            "description": "擁有系統所有權限",
            "permissions": "all",
        },
        {
            "code": "MANAGER",
            "name": "店長",
            "description": "門市管理權限",
            "permissions": "store.read,store.write,order.read,order.write,inventory.read,inventory.write",
        },
        {
            "code": "CASHIER",
            "name": "收銀員",
            "description": "POS 收銀權限",
            "permissions": "order.read,order.write,product.read,customer.read",
        },
        {
            "code": "WAREHOUSE",
            "name": "倉管人員",
            "description": "倉庫管理權限",
            "permissions": "inventory.read,inventory.write,product.read",
        },
    ]

    roles = {}
    for data in roles_data:
        role = Role(**data)
        session.add(role)
        roles[data["code"]] = role

    await session.flush()
    print(f"  已建立 {len(roles)} 個角色")
    return roles


async def create_users(session: AsyncSession, roles: dict) -> dict:
    """建立使用者"""
    print("建立使用者...")
    users_data = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("admin123"),
            "full_name": "系統管理員",
            "phone": "0912345678",
            "is_superuser": True,
            "role_id": roles["ADMIN"].id,
        },
        {
            "username": "manager",
            "email": "manager@example.com",
            "hashed_password": get_password_hash("manager123"),
            "full_name": "王店長",
            "phone": "0923456789",
            "role_id": roles["MANAGER"].id,
        },
        {
            "username": "cashier1",
            "email": "cashier1@example.com",
            "hashed_password": get_password_hash("cashier123"),
            "full_name": "陳小明",
            "phone": "0934567890",
            "role_id": roles["CASHIER"].id,
        },
        {
            "username": "cashier2",
            "email": "cashier2@example.com",
            "hashed_password": get_password_hash("cashier123"),
            "full_name": "林小華",
            "phone": "0945678901",
            "role_id": roles["CASHIER"].id,
        },
        {
            "username": "warehouse",
            "email": "warehouse@example.com",
            "hashed_password": get_password_hash("warehouse123"),
            "full_name": "李倉管",
            "phone": "0956789012",
            "role_id": roles["WAREHOUSE"].id,
        },
    ]

    users = {}
    for data in users_data:
        user = User(**data)
        session.add(user)
        users[data["username"]] = user

    await session.flush()
    print(f"  已建立 {len(users)} 個使用者")
    return users


async def create_warehouses(session: AsyncSession) -> dict:
    """建立倉庫"""
    print("建立倉庫...")
    warehouses_data = [
        {"code": "WH001", "name": "總倉", "address": "新北市中和區建一路100號"},
        {"code": "WH002", "name": "北區倉", "address": "台北市內湖區瑞光路200號"},
    ]

    warehouses = {}
    for data in warehouses_data:
        warehouse = Warehouse(**data)
        session.add(warehouse)
        warehouses[data["code"]] = warehouse

    await session.flush()
    print(f"  已建立 {len(warehouses)} 個倉庫")
    return warehouses


async def create_stores(session: AsyncSession, warehouses: dict) -> dict:
    """建立門市"""
    print("建立門市...")
    stores_data = [
        {
            "code": "ST001",
            "name": "台北旗艦店",
            "address": "台北市信義區信義路五段7號",
            "phone": "02-27001234",
            "warehouse_id": warehouses["WH001"].id,
        },
        {
            "code": "ST002",
            "name": "新北板橋店",
            "address": "新北市板橋區中山路一段100號",
            "phone": "02-29601234",
            "warehouse_id": warehouses["WH001"].id,
        },
        {
            "code": "ST003",
            "name": "內湖店",
            "address": "台北市內湖區成功路四段30號",
            "phone": "02-27901234",
            "warehouse_id": warehouses["WH002"].id,
        },
    ]

    stores = {}
    for data in stores_data:
        store = Store(**data)
        session.add(store)
        stores[data["code"]] = store

    await session.flush()
    print(f"  已建立 {len(stores)} 個門市")
    return stores


async def create_customer_levels(session: AsyncSession) -> dict:
    """建立客戶等級"""
    print("建立客戶等級...")
    levels_data = [
        {
            "code": "NORMAL",
            "name": "一般會員",
            "discount_rate": Decimal("0.00"),
            "min_spending": Decimal("0.00"),
            "description": "基本會員",
        },
        {
            "code": "SILVER",
            "name": "銀卡會員",
            "discount_rate": Decimal("0.05"),
            "min_spending": Decimal("5000.00"),
            "description": "累計消費滿5000",
        },
        {
            "code": "GOLD",
            "name": "金卡會員",
            "discount_rate": Decimal("0.10"),
            "min_spending": Decimal("20000.00"),
            "description": "累計消費滿20000",
        },
        {
            "code": "VIP",
            "name": "VIP會員",
            "discount_rate": Decimal("0.15"),
            "min_spending": Decimal("50000.00"),
            "description": "累計消費滿50000",
        },
    ]

    levels = {}
    for data in levels_data:
        level = CustomerLevel(**data)
        session.add(level)
        levels[data["code"]] = level

    await session.flush()
    print(f"  已建立 {len(levels)} 個客戶等級")
    return levels


async def create_customers(session: AsyncSession, levels: dict) -> dict:
    """建立客戶"""
    print("建立客戶...")
    customers_data = [
        {
            "code": "C001",
            "name": "張三",
            "phone": "0911111111",
            "email": "zhang3@example.com",
            "birthday": date(1990, 5, 15),
            "level_id": levels["GOLD"].id,
            "total_spending": Decimal("25000.00"),
            "points": 2500,
        },
        {
            "code": "C002",
            "name": "李四",
            "phone": "0922222222",
            "email": "li4@example.com",
            "birthday": date(1985, 8, 20),
            "level_id": levels["SILVER"].id,
            "total_spending": Decimal("8000.00"),
            "points": 800,
        },
        {
            "code": "C003",
            "name": "王五",
            "phone": "0933333333",
            "email": "wang5@example.com",
            "birthday": date(1995, 12, 1),
            "level_id": levels["NORMAL"].id,
            "total_spending": Decimal("2000.00"),
            "points": 200,
        },
        {
            "code": "C004",
            "name": "趙六",
            "phone": "0944444444",
            "email": "zhao6@example.com",
            "birthday": date(1988, 3, 10),
            "level_id": levels["VIP"].id,
            "total_spending": Decimal("55000.00"),
            "points": 5500,
        },
        {
            "code": "C005",
            "name": "陳七",
            "phone": "0955555555",
            "email": "chen7@example.com",
            "birthday": date(1992, 7, 25),
            "level_id": levels["NORMAL"].id,
            "total_spending": Decimal("1500.00"),
            "points": 150,
        },
    ]

    customers = {}
    for data in customers_data:
        customer = Customer(**data)
        session.add(customer)
        customers[data["code"]] = customer

    await session.flush()
    print(f"  已建立 {len(customers)} 個客戶")
    return customers


async def create_suppliers(session: AsyncSession) -> dict:
    """建立供應商"""
    print("建立供應商...")
    suppliers_data = [
        {
            "code": "SUP001",
            "name": "統一企業",
            "contact_name": "陳經理",
            "phone": "02-27001111",
            "email": "chen@uni.com.tw",
            "tax_id": "22099131",
            "payment_terms": 30,
        },
        {
            "code": "SUP002",
            "name": "味全食品",
            "contact_name": "林經理",
            "phone": "02-25551111",
            "email": "lin@weichuan.com.tw",
            "tax_id": "11111111",
            "payment_terms": 45,
        },
        {
            "code": "SUP003",
            "name": "可口可樂",
            "contact_name": "王經理",
            "phone": "02-87771111",
            "email": "wang@coca-cola.com.tw",
            "tax_id": "22222222",
            "payment_terms": 30,
        },
    ]

    suppliers = {}
    for data in suppliers_data:
        supplier = Supplier(**data)
        session.add(supplier)
        suppliers[data["code"]] = supplier

    await session.flush()
    print(f"  已建立 {len(suppliers)} 個供應商")
    return suppliers


async def create_units(session: AsyncSession) -> dict:
    """建立單位"""
    print("建立單位...")
    units_data = [
        {"code": "PCS", "name": "個"},
        {"code": "BOX", "name": "箱"},
        {"code": "BTL", "name": "瓶"},
        {"code": "CAN", "name": "罐"},
        {"code": "PKG", "name": "包"},
        {"code": "KG", "name": "公斤"},
    ]

    units = {}
    for data in units_data:
        unit = Unit(**data)
        session.add(unit)
        units[data["code"]] = unit

    await session.flush()
    print(f"  已建立 {len(units)} 個單位")
    return units


async def create_tax_types(session: AsyncSession) -> dict:
    """建立稅別"""
    print("建立稅別...")
    tax_types_data = [
        {"code": "TAX5", "name": "應稅5%", "rate": Decimal("0.05")},
        {"code": "TAX0", "name": "零稅率", "rate": Decimal("0.00")},
        {"code": "EXEMPT", "name": "免稅", "rate": Decimal("0.00")},
    ]

    tax_types = {}
    for data in tax_types_data:
        tax_type = TaxType(**data)
        session.add(tax_type)
        tax_types[data["code"]] = tax_type

    await session.flush()
    print(f"  已建立 {len(tax_types)} 個稅別")
    return tax_types


async def create_categories(session: AsyncSession) -> dict:
    """建立商品類別"""
    print("建立商品類別...")
    categories_data = [
        {"code": "BEV", "name": "飲料", "level": 1, "sort_order": 1},
        {"code": "FOOD", "name": "食品", "level": 1, "sort_order": 2},
        {"code": "SNACK", "name": "零食", "level": 1, "sort_order": 3},
        {"code": "DAILY", "name": "日用品", "level": 1, "sort_order": 4},
    ]

    categories = {}
    for data in categories_data:
        category = Category(**data)
        session.add(category)
        categories[data["code"]] = category

    await session.flush()
    print(f"  已建立 {len(categories)} 個類別")
    return categories


async def create_products(
    session: AsyncSession,
    categories: dict,
    units: dict,
    tax_types: dict,
    suppliers: dict,
) -> dict:
    """建立商品"""
    print("建立商品...")
    products_data = [
        {
            "code": "P001",
            "barcode": "4710088401234",
            "name": "可口可樂 350ml",
            "cost_price": Decimal("15.00"),
            "selling_price": Decimal("25.00"),
            "min_stock": 20,
            "max_stock": 200,
            "category_id": categories["BEV"].id,
            "unit_id": units["CAN"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP003"].id,
        },
        {
            "code": "P002",
            "barcode": "4710088401235",
            "name": "雪碧 350ml",
            "cost_price": Decimal("15.00"),
            "selling_price": Decimal("25.00"),
            "min_stock": 20,
            "max_stock": 200,
            "category_id": categories["BEV"].id,
            "unit_id": units["CAN"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP003"].id,
        },
        {
            "code": "P003",
            "barcode": "4710088501234",
            "name": "統一布丁",
            "cost_price": Decimal("20.00"),
            "selling_price": Decimal("35.00"),
            "min_stock": 15,
            "max_stock": 100,
            "category_id": categories["FOOD"].id,
            "unit_id": units["PCS"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP001"].id,
        },
        {
            "code": "P004",
            "barcode": "4710088601234",
            "name": "樂事洋芋片",
            "cost_price": Decimal("25.00"),
            "selling_price": Decimal("45.00"),
            "min_stock": 10,
            "max_stock": 80,
            "category_id": categories["SNACK"].id,
            "unit_id": units["PKG"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP002"].id,
        },
        {
            "code": "P005",
            "barcode": "4710088701234",
            "name": "舒潔衛生紙",
            "cost_price": Decimal("80.00"),
            "selling_price": Decimal("129.00"),
            "min_stock": 10,
            "max_stock": 50,
            "category_id": categories["DAILY"].id,
            "unit_id": units["PKG"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP002"].id,
        },
        {
            "code": "P006",
            "barcode": "4710088801234",
            "name": "茶裏王 綠茶 600ml",
            "cost_price": Decimal("18.00"),
            "selling_price": Decimal("29.00"),
            "min_stock": 20,
            "max_stock": 150,
            "category_id": categories["BEV"].id,
            "unit_id": units["BTL"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP001"].id,
        },
        {
            "code": "P007",
            "barcode": "4710088901234",
            "name": "光泉鮮奶 936ml",
            "cost_price": Decimal("55.00"),
            "selling_price": Decimal("79.00"),
            "min_stock": 10,
            "max_stock": 50,
            "category_id": categories["FOOD"].id,
            "unit_id": units["BTL"].id,
            "tax_type_id": tax_types["TAX5"].id,
            "supplier_id": suppliers["SUP002"].id,
        },
    ]

    products = {}
    for data in products_data:
        product = Product(**data)
        session.add(product)
        products[data["code"]] = product

    await session.flush()
    print(f"  已建立 {len(products)} 個商品")
    return products


async def create_inventories(
    session: AsyncSession,
    products: dict,
    warehouses: dict,
) -> None:
    """建立庫存"""
    print("建立庫存...")
    count = 0

    for product_code, product in products.items():
        for warehouse_code, warehouse in warehouses.items():
            inventory = Inventory(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=random.randint(30, 100),
            )
            session.add(inventory)
            count += 1

    await session.flush()
    print(f"  已建立 {count} 筆庫存記錄")


async def create_supplier_prices(
    session: AsyncSession,
    products: dict,
    suppliers: dict,
) -> None:
    """建立供應商報價"""
    print("建立供應商報價...")
    count = 0
    today = date.today()

    for product_code, product in products.items():
        # 每個商品有 1-2 個供應商報價
        supplier_list = list(suppliers.values())
        for supplier in random.sample(supplier_list, min(2, len(supplier_list))):
            supplier_price = SupplierPrice(
                supplier_id=supplier.id,
                product_id=product.id,
                unit_price=product.cost_price * Decimal(str(random.uniform(0.9, 1.1))),
                min_order_quantity=random.choice([1, 5, 10]),
                lead_time_days=random.randint(1, 7),
                effective_date=today - timedelta(days=30),
                expiry_date=today + timedelta(days=365),
            )
            session.add(supplier_price)
            count += 1

    await session.flush()
    print(f"  已建立 {count} 筆供應商報價")


async def create_promotions(session: AsyncSession) -> dict:
    """建立促銷活動"""
    print("建立促銷活動...")
    now = datetime.now(timezone.utc)
    promotions_data = [
        {
            "code": "PROMO001",
            "name": "新春優惠",
            "description": "全館商品 9 折",
            "promotion_type": PromotionType.PERCENTAGE,
            "discount_value": Decimal("10.00"),
            "min_purchase": Decimal("100.00"),
            "max_discount": Decimal("500.00"),
            "start_date": now - timedelta(days=10),
            "end_date": now + timedelta(days=20),
            "usage_limit": 1000,
            "used_count": 150,
        },
        {
            "code": "PROMO002",
            "name": "滿千折百",
            "description": "滿 1000 元折 100 元",
            "promotion_type": PromotionType.FIXED_AMOUNT,
            "discount_value": Decimal("100.00"),
            "min_purchase": Decimal("1000.00"),
            "start_date": now - timedelta(days=5),
            "end_date": now + timedelta(days=25),
            "usage_limit": 500,
            "used_count": 80,
        },
        {
            "code": "PROMO003",
            "name": "飲料買二送一",
            "description": "飲料類商品買二送一",
            "promotion_type": PromotionType.BUY_X_GET_Y,
            "discount_value": Decimal("0.00"),
            "min_purchase": Decimal("0.00"),
            "start_date": now,
            "end_date": now + timedelta(days=14),
            "usage_limit": 200,
            "used_count": 30,
        },
    ]

    promotions = {}
    for data in promotions_data:
        promotion = Promotion(**data)
        session.add(promotion)
        promotions[data["code"]] = promotion

    await session.flush()
    print(f"  已建立 {len(promotions)} 個促銷活動")
    return promotions


async def create_coupons(session: AsyncSession, customers: dict) -> dict:
    """建立優惠券"""
    print("建立優惠券...")
    now = datetime.now(timezone.utc)
    coupons = {}
    count = 0

    # 為每個客戶建立一些優惠券
    for i, (customer_code, customer) in enumerate(customers.items()):
        # 每個客戶 2 張優惠券
        for j in range(2):
            coupon_code = f"CPN{i:03d}{j:02d}"
            coupon = Coupon(
                code=coupon_code,
                name=f"會員專屬折扣券 {coupon_code}",
                discount_type=random.choice([DiscountType.PERCENTAGE, DiscountType.FIXED_AMOUNT]),
                discount_value=Decimal(str(random.choice([5, 10, 50, 100]))),
                min_purchase=Decimal(str(random.choice([100, 200, 500]))),
                max_discount=Decimal("200.00") if random.random() > 0.5 else None,
                start_date=now - timedelta(days=random.randint(0, 10)),
                end_date=now + timedelta(days=random.randint(30, 90)),
                customer_id=customer.id,
                is_used=random.random() < 0.3,  # 30% 已使用
            )
            if coupon.is_used:
                coupon.used_at = now - timedelta(days=random.randint(1, 5))
            session.add(coupon)
            coupons[coupon_code] = coupon
            count += 1

    await session.flush()
    print(f"  已建立 {count} 張優惠券")
    return coupons


async def create_payment_method_settings(session: AsyncSession) -> dict:
    """建立付款方式設定"""
    print("建立付款方式設定...")
    settings_data = [
        {"code": "CASH", "name": "現金", "requires_change": True, "sort_order": 1},
        {"code": "CREDIT_CARD", "name": "信用卡", "requires_authorization": True, "sort_order": 2},
        {"code": "DEBIT_CARD", "name": "金融卡", "requires_authorization": True, "sort_order": 3},
        {"code": "LINE_PAY", "name": "LINE Pay", "requires_authorization": True, "sort_order": 4},
        {"code": "APPLE_PAY", "name": "Apple Pay", "requires_authorization": True, "sort_order": 5},
    ]

    payment_settings = {}
    for data in settings_data:
        setting = PaymentMethodSetting(**data)
        session.add(setting)
        payment_settings[data["code"]] = setting

    await session.flush()
    print(f"  已建立 {len(payment_settings)} 個付款方式設定")
    return payment_settings


async def create_orders(
    session: AsyncSession,
    stores: dict,
    customers: dict,
    products: dict,
    users: dict,
) -> dict:
    """建立訂單"""
    print("建立訂單...")
    orders = {}
    now = datetime.now(timezone.utc)
    store_list = list(stores.values())
    customer_list = list(customers.values())
    product_list = list(products.values())

    for i in range(20):  # 建立 20 筆訂單
        order_number = f"ORD{now.strftime('%Y%m%d')}{i+1:04d}"
        store = random.choice(store_list)
        customer = random.choice(customer_list) if random.random() > 0.3 else None
        order_date = now - timedelta(days=random.randint(0, 30))

        order = Order(
            order_number=order_number,
            store_id=store.id,
            customer_id=customer.id if customer else None,
            status=random.choice([OrderStatus.COMPLETED, OrderStatus.COMPLETED, OrderStatus.PENDING]),
            order_date=order_date,
            created_by=users["cashier1"].id,
        )
        session.add(order)
        await session.flush()

        # 建立訂單明細 (每筆訂單 1-5 個商品)
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        num_items = random.randint(1, 5)

        for selected_product in random.sample(product_list, min(num_items, len(product_list))):
            qty = random.randint(1, 3)
            unit_price = selected_product.selling_price
            item_subtotal = unit_price * qty
            tax_rate = Decimal("0.05")
            item_tax = item_subtotal * tax_rate

            order_item = OrderItem(
                order_id=order.id,
                product_id=selected_product.id,
                product_name=selected_product.name,
                quantity=qty,
                unit_price=unit_price,
                subtotal=item_subtotal,
                tax_rate=tax_rate,
                tax_amount=item_tax,
            )
            session.add(order_item)
            subtotal += item_subtotal
            tax_total += item_tax

        order.subtotal = subtotal
        order.tax_amount = tax_total
        order.total_amount = subtotal + tax_total

        # 建立付款記錄
        if order.status == OrderStatus.COMPLETED:
            payment = Payment(
                order_id=order.id,
                payment_method=random.choice([PaymentMethod.CASH, PaymentMethod.CREDIT_CARD, PaymentMethod.LINE_PAY]),
                amount=order.total_amount,
                status=PaymentStatus.PAID,
                paid_at=order_date,
            )
            session.add(payment)

        orders[order_number] = order

    await session.flush()
    print(f"  已建立 {len(orders)} 筆訂單")
    return orders


async def create_invoices(session: AsyncSession, orders: dict) -> None:
    """建立發票"""
    print("建立發票...")
    count = 0

    for order_number, order in orders.items():
        if order.status == OrderStatus.COMPLETED:
            invoice_no = f"AA{order.order_date.strftime('%Y%m%d')}{count+1:04d}"
            invoice = Invoice(
                invoice_no=invoice_no,
                order_id=order.id,
                invoice_date=order.order_date,
                invoice_type=random.choice([InvoiceType.B2C, InvoiceType.B2C_CARRIER]),
                carrier_type=CarrierType.MOBILE if random.random() > 0.5 else None,
                carrier_no="/ABC1234" if random.random() > 0.5 else None,
                sales_amount=order.subtotal,
                tax_amount=order.tax_amount,
                total_amount=order.total_amount,
                random_number=f"{random.randint(1000, 9999)}",
            )
            session.add(invoice)
            count += 1

    await session.flush()
    print(f"  已建立 {count} 張發票")


async def create_sales_returns(
    session: AsyncSession,
    orders: dict,
    stores: dict,
    products: dict,
) -> None:
    """建立銷售退貨"""
    print("建立銷售退貨...")
    count = 0
    now = datetime.now(timezone.utc)

    # 挑選幾筆已完成的訂單來退貨
    completed_orders = [o for o in orders.values() if o.status == OrderStatus.COMPLETED]
    for order in random.sample(completed_orders, min(3, len(completed_orders))):
        return_number = f"SR{now.strftime('%Y%m%d')}{count+1:04d}"
        sales_return = SalesReturn(
            return_number=return_number,
            order_id=order.id,
            store_id=order.store_id,
            customer_id=order.customer_id,
            status=random.choice([SalesReturnStatus.COMPLETED, SalesReturnStatus.PENDING]),
            reason=random.choice([ReturnReason.DEFECTIVE, ReturnReason.CHANGE_OF_MIND]),
            reason_detail="客戶要求退貨",
            total_amount=order.total_amount * Decimal("0.5"),
            return_date=now - timedelta(days=random.randint(1, 5)),
        )
        session.add(sales_return)
        await session.flush()

        # 退貨明細
        product = random.choice(list(products.values()))
        return_item = SalesReturnItem(
            sales_return_id=sales_return.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=product.selling_price,
            subtotal=product.selling_price,
        )
        session.add(return_item)
        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆銷售退貨")


async def create_purchase_orders(
    session: AsyncSession,
    suppliers: dict,
    warehouses: dict,
    products: dict,
    users: dict,
) -> dict:
    """建立採購單"""
    print("建立採購單...")
    purchase_orders = {}
    today = date.today()
    supplier_list = list(suppliers.values())
    warehouse_list = list(warehouses.values())
    product_list = list(products.values())

    for i in range(10):
        order_number = f"PO{today.strftime('%Y%m%d')}{i+1:04d}"
        supplier = random.choice(supplier_list)
        warehouse = random.choice(warehouse_list)

        po = PurchaseOrder(
            order_number=order_number,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            order_date=today - timedelta(days=random.randint(0, 30)),
            expected_date=today + timedelta(days=random.randint(1, 14)),
            status=random.choice([
                PurchaseOrderStatus.COMPLETED,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.PENDING,
            ]),
            created_by=users["warehouse"].id,
        )
        if po.status in [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.COMPLETED]:
            po.approved_by = users["manager"].id
            po.approved_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5))

        session.add(po)
        await session.flush()

        # 採購單明細
        total = Decimal("0.00")
        for product in random.sample(product_list, random.randint(2, 5)):
            qty = random.randint(10, 50)
            unit_price = product.cost_price
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price,
                received_quantity=qty if po.status == PurchaseOrderStatus.COMPLETED else 0,
            )
            session.add(item)
            total += unit_price * qty

        po.total_amount = total
        purchase_orders[order_number] = po

    await session.flush()
    print(f"  已建立 {len(purchase_orders)} 筆採購單")
    return purchase_orders


async def create_purchase_receipts(
    session: AsyncSession,
    purchase_orders: dict,
    products: dict,
    users: dict,
) -> None:
    """建立驗收單"""
    print("建立驗收單...")
    count = 0
    today = date.today()

    completed_pos = [po for po in purchase_orders.values() if po.status == PurchaseOrderStatus.COMPLETED]
    for po in completed_pos:
        receipt_number = f"PR{today.strftime('%Y%m%d')}{count+1:04d}"
        receipt = PurchaseReceipt(
            receipt_number=receipt_number,
            purchase_order_id=po.id,
            receipt_date=today - timedelta(days=random.randint(1, 10)),
            status=PurchaseReceiptStatus.COMPLETED,
            completed_by=users["warehouse"].id,
            completed_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5)),
        )
        session.add(receipt)
        await session.flush()

        # 驗收單明細
        for product in random.sample(list(products.values()), random.randint(1, 3)):
            item = PurchaseReceiptItem(
                purchase_receipt_id=receipt.id,
                product_id=product.id,
                received_quantity=random.randint(10, 30),
                rejected_quantity=random.randint(0, 2),
            )
            session.add(item)

        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆驗收單")


async def create_purchase_returns(
    session: AsyncSession,
    suppliers: dict,
    warehouses: dict,
    products: dict,
    users: dict,
) -> None:
    """建立採購退貨"""
    print("建立採購退貨...")
    count = 0
    today = date.today()
    supplier_list = list(suppliers.values())
    warehouse_list = list(warehouses.values())
    product_list = list(products.values())

    for i in range(3):
        return_number = f"PRT{today.strftime('%Y%m%d')}{i+1:04d}"
        supplier = random.choice(supplier_list)
        warehouse = random.choice(warehouse_list)

        pr = PurchaseReturn(
            return_number=return_number,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            return_date=today - timedelta(days=random.randint(1, 15)),
            status=random.choice([PurchaseReturnStatus.COMPLETED, PurchaseReturnStatus.APPROVED]),
            reason="商品瑕疵",
            created_by=users["warehouse"].id,
        )
        if pr.status in [PurchaseReturnStatus.APPROVED, PurchaseReturnStatus.COMPLETED]:
            pr.approved_by = users["manager"].id
            pr.approved_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 3))

        session.add(pr)
        await session.flush()

        # 退貨明細
        total = Decimal("0.00")
        for product in random.sample(product_list, random.randint(1, 2)):
            qty = random.randint(1, 5)
            unit_price = product.cost_price
            item = PurchaseReturnItem(
                purchase_return_id=pr.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price,
                reason="瑕疵品",
            )
            session.add(item)
            total += unit_price * qty

        pr.total_amount = total
        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆採購退貨")


async def create_stock_transfers(
    session: AsyncSession,
    warehouses: dict,
    products: dict,
    users: dict,
) -> None:
    """建立庫存調撥"""
    print("建立庫存調撥...")
    count = 0
    today = date.today()
    warehouse_list = list(warehouses.values())
    product_list = list(products.values())

    for i in range(5):
        transfer_number = f"ST{today.strftime('%Y%m%d')}{i+1:04d}"
        source_warehouse = warehouse_list[0]
        dest_warehouse = warehouse_list[1] if len(warehouse_list) > 1 else warehouse_list[0]

        transfer = StockTransfer(
            transfer_number=transfer_number,
            source_warehouse_id=source_warehouse.id,
            destination_warehouse_id=dest_warehouse.id,
            transfer_date=today - timedelta(days=random.randint(1, 20)),
            expected_date=today - timedelta(days=random.randint(0, 10)),
            status=random.choice([StockTransferStatus.COMPLETED, StockTransferStatus.IN_TRANSIT, StockTransferStatus.APPROVED]),
            created_by=users["warehouse"].id,
        )
        if transfer.status in [StockTransferStatus.APPROVED, StockTransferStatus.IN_TRANSIT, StockTransferStatus.COMPLETED]:
            transfer.approved_by = users["manager"].id
            transfer.approved_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))
        if transfer.status == StockTransferStatus.COMPLETED:
            transfer.received_by = users["warehouse"].id
            transfer.received_date = today - timedelta(days=random.randint(0, 5))

        session.add(transfer)
        await session.flush()

        # 調撥明細
        for product in random.sample(product_list, random.randint(2, 4)):
            qty = random.randint(5, 20)
            item = StockTransferItem(
                stock_transfer_id=transfer.id,
                product_id=product.id,
                quantity=qty,
                received_quantity=qty if transfer.status == StockTransferStatus.COMPLETED else None,
            )
            session.add(item)

        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆庫存調撥")


async def create_stock_counts(
    session: AsyncSession,
    warehouses: dict,
    products: dict,
    users: dict,
) -> None:
    """建立庫存盤點"""
    print("建立庫存盤點...")
    count = 0
    today = date.today()
    warehouse_list = list(warehouses.values())
    product_list = list(products.values())

    for i, warehouse in enumerate(warehouse_list):
        count_number = f"SC{today.strftime('%Y%m%d')}{i+1:04d}"
        stock_count = StockCount(
            count_number=count_number,
            warehouse_id=warehouse.id,
            count_date=today - timedelta(days=random.randint(1, 30)),
            status=random.choice([StockCountStatus.COMPLETED, StockCountStatus.IN_PROGRESS]),
            created_by=users["warehouse"].id,
        )
        if stock_count.status == StockCountStatus.COMPLETED:
            stock_count.completed_by = users["warehouse"].id
            stock_count.completed_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5))

        session.add(stock_count)
        await session.flush()

        # 盤點明細
        for product in random.sample(product_list, random.randint(3, 5)):
            system_qty = random.randint(30, 100)
            actual_qty = system_qty + random.randint(-5, 5)
            item = StockCountItem(
                stock_count_id=stock_count.id,
                product_id=product.id,
                system_quantity=system_qty,
                actual_quantity=actual_qty,
                difference=actual_qty - system_qty,
            )
            session.add(item)

        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆庫存盤點")


async def create_inventory_transactions(
    session: AsyncSession,
    products: dict,
    warehouses: dict,
    users: dict,
) -> None:
    """建立庫存異動記錄"""
    print("建立庫存異動記錄...")
    count = 0
    product_list = list(products.values())
    warehouse_list = list(warehouses.values())

    for product in product_list:
        for warehouse in warehouse_list:
            # 每個商品/倉庫組合建立幾筆異動記錄
            for _ in range(random.randint(2, 5)):
                trans_type = random.choice([
                    TransactionType.PURCHASE,
                    TransactionType.SALE,
                    TransactionType.ADJUSTMENT,
                ])
                before_qty = random.randint(20, 80)
                qty_change = random.randint(-10, 30)
                after_qty = before_qty + qty_change

                transaction = InventoryTransaction(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    transaction_type=trans_type,
                    quantity=qty_change,
                    before_quantity=before_qty,
                    after_quantity=after_qty,
                    reference_type="Order" if trans_type == TransactionType.SALE else "PurchaseOrder",
                    reference_id=random.randint(1, 10),
                    created_by=users["warehouse"].id,
                )
                session.add(transaction)
                count += 1

    await session.flush()
    print(f"  已建立 {count} 筆庫存異動記錄")


async def create_cashier_shifts(
    session: AsyncSession,
    stores: dict,
    users: dict,
) -> None:
    """建立收銀班次"""
    print("建立收銀班次...")
    count = 0
    today = date.today()
    store_list = list(stores.values())

    for days_ago in range(7):  # 最近 7 天的班次
        shift_date = today - timedelta(days=days_ago)
        for store in store_list:
            shift = CashierShift(
                store_id=store.id,
                pos_id=f"POS{store.id:02d}",
                cashier_id=users["cashier1"].id,
                shift_date=shift_date,
                start_time=datetime.combine(shift_date, datetime.min.time().replace(hour=9)),
                opening_cash=Decimal("5000.00"),
                status=ShiftStatus.CLOSED if days_ago > 0 else ShiftStatus.OPEN,
                total_sales=Decimal(str(random.randint(10000, 50000))),
                total_transactions=random.randint(20, 100),
                total_cash_sales=Decimal(str(random.randint(3000, 20000))),
                total_card_sales=Decimal(str(random.randint(5000, 25000))),
                total_other_sales=Decimal(str(random.randint(1000, 5000))),
            )
            if shift.status == ShiftStatus.CLOSED:
                shift.end_time = datetime.combine(shift_date, datetime.min.time().replace(hour=18))
                shift.expected_cash = shift.opening_cash + shift.total_cash_sales
                shift.actual_cash = shift.expected_cash + Decimal(str(random.randint(-50, 50)))
                shift.cash_difference = shift.actual_cash - shift.expected_cash
                shift.approved_by = users["manager"].id

            session.add(shift)
            count += 1

    await session.flush()
    print(f"  已建立 {count} 筆收銀班次")


async def create_points_logs(session: AsyncSession, customers: dict) -> None:
    """建立點數異動記錄"""
    print("建立點數異動記錄...")
    count = 0

    for customer in customers.values():
        # 每個客戶幾筆點數記錄
        balance = 0
        for i in range(random.randint(3, 8)):
            log_type = random.choice([PointsLogType.EARN, PointsLogType.EARN, PointsLogType.REDEEM, PointsLogType.BONUS])
            if log_type == PointsLogType.REDEEM and balance < 100:
                log_type = PointsLogType.EARN

            points = random.randint(50, 500) if log_type != PointsLogType.REDEEM else -random.randint(50, min(balance, 300))
            balance += points

            log = PointsLog(
                customer_id=customer.id,
                type=log_type,
                points=points,
                balance=balance,
                reference_type="Order" if log_type in [PointsLogType.EARN, PointsLogType.REDEEM] else None,
                reference_id=random.randint(1, 20) if log_type in [PointsLogType.EARN, PointsLogType.REDEEM] else None,
                description=f"{'消費獲得' if log_type == PointsLogType.EARN else '點數折抵' if log_type == PointsLogType.REDEEM else '活動贈點'}",
            )
            session.add(log)
            count += 1

    await session.flush()
    print(f"  已建立 {count} 筆點數異動記錄")


async def create_audit_logs(session: AsyncSession, users: dict) -> None:
    """建立稽核日誌"""
    print("建立稽核日誌...")
    count = 0
    now = datetime.now(timezone.utc)
    user_list = list(users.values())

    modules = ["users", "products", "orders", "inventory", "customers"]
    for i in range(30):
        user = random.choice(user_list)
        log = AuditLog(
            user_id=user.id,
            username=user.username,
            action_type=random.choice([ActionType.CREATE, ActionType.UPDATE, ActionType.VIEW, ActionType.LOGIN]),
            module=random.choice(modules),
            target_id=random.randint(1, 100),
            target_name=f"測試資料 {i+1}",
            ip_address=f"192.168.1.{random.randint(1, 255)}",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            description=f"操作說明 {i+1}",
            created_at=now - timedelta(hours=random.randint(0, 720)),
        )
        session.add(log)
        count += 1

    await session.flush()
    print(f"  已建立 {count} 筆稽核日誌")


async def create_report_templates(session: AsyncSession, users: dict) -> dict:
    """建立報表範本"""
    print("建立報表範本...")
    templates_data = [
        {
            "code": "RPT_DAILY_SALES",
            "name": "每日銷售報表",
            "description": "統計每日銷售數據",
            "report_type": ReportType.SALES_DAILY,
            "is_system": True,
            "is_public": True,
            "owner_id": users["admin"].id,
        },
        {
            "code": "RPT_INVENTORY",
            "name": "庫存報表",
            "description": "顯示目前庫存狀況",
            "report_type": ReportType.INVENTORY,
            "is_system": True,
            "is_public": True,
            "owner_id": users["admin"].id,
        },
        {
            "code": "RPT_TOP_PRODUCTS",
            "name": "熱銷商品報表",
            "description": "統計熱銷商品排行",
            "report_type": ReportType.TOP_PRODUCTS,
            "is_system": True,
            "is_public": True,
            "owner_id": users["admin"].id,
        },
        {
            "code": "RPT_CUSTOMER",
            "name": "客戶分析報表",
            "description": "客戶消費分析",
            "report_type": ReportType.CUSTOMER,
            "is_system": False,
            "is_public": False,
            "owner_id": users["manager"].id,
        },
    ]

    templates = {}
    for data in templates_data:
        template = ReportTemplate(**data)
        session.add(template)
        templates[data["code"]] = template

    await session.flush()
    print(f"  已建立 {len(templates)} 個報表範本")
    return templates


async def create_report_schedules(
    session: AsyncSession,
    users: dict,
) -> None:
    """建立報表排程"""
    print("建立報表排程...")
    now = datetime.now(timezone.utc)
    schedules_data = [
        {
            "name": "每日銷售報表",
            "report_type": "SALES_DAILY",
            "frequency": ScheduleFrequency.DAILY,
            "schedule_time": "08:00",
            "recipients": ["manager@example.com", "admin@example.com"],
            "owner_id": users["admin"].id,
            "next_run_at": now + timedelta(days=1),
        },
        {
            "name": "每週庫存報表",
            "report_type": "INVENTORY",
            "frequency": ScheduleFrequency.WEEKLY,
            "schedule_time": "09:00",
            "day_of_week": 1,  # 週一
            "recipients": ["warehouse@example.com"],
            "owner_id": users["admin"].id,
            "next_run_at": now + timedelta(days=7),
        },
        {
            "name": "每月客戶分析",
            "report_type": "CUSTOMER",
            "frequency": ScheduleFrequency.MONTHLY,
            "schedule_time": "10:00",
            "day_of_month": 1,
            "recipients": ["manager@example.com"],
            "owner_id": users["manager"].id,
            "next_run_at": now + timedelta(days=30),
        },
    ]

    count = 0
    for data in schedules_data:
        schedule = ReportSchedule(**data)
        session.add(schedule)
        await session.flush()

        # 建立一些執行記錄
        for i in range(random.randint(2, 5)):
            execution = ReportExecution(
                schedule_id=schedule.id,
                status=random.choice([ExecutionStatus.SUCCESS, ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]),
                started_at=now - timedelta(days=i * 7),
                completed_at=now - timedelta(days=i * 7) + timedelta(minutes=random.randint(1, 5)),
                duration_seconds=random.uniform(30, 300),
                file_path=f"/reports/{schedule.report_type}_{i}.xlsx" if random.random() > 0.2 else None,
                file_size=random.randint(10000, 500000) if random.random() > 0.2 else None,
                triggered_by="schedule",
            )
            session.add(execution)

        count += 1

    await session.flush()
    print(f"  已建立 {count} 個報表排程")


async def create_system_parameters(session: AsyncSession) -> None:
    """建立系統參數"""
    print("建立系統參數...")
    params_data = [
        {
            "param_code": "POINTS_RATE",
            "param_name": "點數累積比率",
            "param_category": "POINTS",
            "param_type": ParamType.DECIMAL,
            "param_value": "0.01",
            "default_value": "0.01",
            "description": "每消費 1 元累積的點數比率",
        },
        {
            "param_code": "POINTS_EXPIRY_DAYS",
            "param_name": "點數有效天數",
            "param_category": "POINTS",
            "param_type": ParamType.INT,
            "param_value": "365",
            "default_value": "365",
            "description": "點數有效期限（天）",
        },
        {
            "param_code": "TAX_RATE",
            "param_name": "預設稅率",
            "param_category": "TAX",
            "param_type": ParamType.DECIMAL,
            "param_value": "0.05",
            "default_value": "0.05",
            "description": "預設營業稅率",
        },
        {
            "param_code": "INVOICE_PREFIX",
            "param_name": "發票字軌",
            "param_category": "INVOICE",
            "param_type": ParamType.STRING,
            "param_value": "AA",
            "default_value": "AA",
            "description": "目前使用的發票字軌",
        },
        {
            "param_code": "LOW_STOCK_ALERT",
            "param_name": "低庫存警示",
            "param_category": "INVENTORY",
            "param_type": ParamType.BOOLEAN,
            "param_value": "true",
            "default_value": "true",
            "description": "是否啟用低庫存警示",
        },
        {
            "param_code": "ORDER_NUMBER_PREFIX",
            "param_name": "訂單編號前綴",
            "param_category": "ORDER",
            "param_type": ParamType.STRING,
            "param_value": "ORD",
            "default_value": "ORD",
            "description": "訂單編號的前綴字串",
        },
    ]

    count = 0
    for data in params_data:
        param = SystemParameter(**data)
        session.add(param)
        count += 1

    await session.flush()
    print(f"  已建立 {count} 個系統參數")


async def main():
    """主程式"""
    print("=" * 50)
    print("FastAPI Demo - Seed Data (完整版)")
    print("=" * 50)

    # 建立資料庫引擎
    async_url = settings.DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
    engine = create_async_engine(async_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # 檢查是否已有資料
            result = await session.execute(select(Role))
            if result.first():
                print("\n資料庫已有資料，跳過 Seed Data")
                print("如需重新建立，請先清空資料庫")
                return

            # 建立基礎資料
            roles = await create_roles(session)
            users = await create_users(session, roles)
            warehouses = await create_warehouses(session)
            stores = await create_stores(session, warehouses)
            levels = await create_customer_levels(session)
            customers = await create_customers(session, levels)
            suppliers = await create_suppliers(session)
            units = await create_units(session)
            tax_types = await create_tax_types(session)
            categories = await create_categories(session)
            products = await create_products(
                session, categories, units, tax_types, suppliers
            )
            await create_inventories(session, products, warehouses)

            # 建立供應商報價
            await create_supplier_prices(session, products, suppliers)

            # 建立促銷與優惠券
            await create_promotions(session)
            await create_coupons(session, customers)

            # 建立付款方式設定
            await create_payment_method_settings(session)

            # 建立訂單相關
            orders = await create_orders(session, stores, customers, products, users)
            await create_invoices(session, orders)
            await create_sales_returns(session, orders, stores, products)

            # 建立採購相關
            purchase_orders = await create_purchase_orders(
                session, suppliers, warehouses, products, users
            )
            await create_purchase_receipts(session, purchase_orders, products, users)
            await create_purchase_returns(session, suppliers, warehouses, products, users)

            # 建立庫存相關
            await create_stock_transfers(session, warehouses, products, users)
            await create_stock_counts(session, warehouses, products, users)
            await create_inventory_transactions(session, products, warehouses, users)

            # 建立班次
            await create_cashier_shifts(session, stores, users)

            # 建立點數記錄
            await create_points_logs(session, customers)

            # 建立稽核日誌
            await create_audit_logs(session, users)

            # 建立報表相關
            await create_report_templates(session, users)
            await create_report_schedules(session, users)

            # 建立系統參數
            await create_system_parameters(session)

            # 提交所有變更
            await session.commit()

            print("\n" + "=" * 50)
            print("Seed Data 建立完成！")
            print("=" * 50)
            print("\n測試帳號：")
            print("  管理員: admin / admin123")
            print("  店長: manager / manager123")
            print("  收銀員: cashier1 / cashier123")
            print("  收銀員: cashier2 / cashier123")
            print("  倉管: warehouse / warehouse123")

        except Exception as e:
            await session.rollback()
            print(f"\n錯誤: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
