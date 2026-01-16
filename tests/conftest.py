"""
Pytest 共用 Fixtures

提供測試所需的共用設定和資源。
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlmodel import SQLModel

from app.kamesan.core.config import settings
from app.kamesan.core.security import get_password_hash
from app.kamesan.core.database import get_async_session
from app.main import app
from app.kamesan.models.user import Role, User
from app.kamesan.models.product import Category, Product, TaxType, Unit
from app.kamesan.models.customer import Customer, CustomerLevel
from app.kamesan.models.store import Store, Warehouse
from app.kamesan.models.supplier import Supplier
from app.kamesan.models.inventory import Inventory
from app.kamesan.models.order import Order, OrderItem, OrderStatus, Payment, PaymentMethod, PaymentStatus
from app.kamesan.models.promotion import Promotion, Coupon, PromotionType, DiscountType
from app.kamesan.models.purchase import (
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus,
    PurchaseReceipt, PurchaseReceiptItem, PurchaseReceiptStatus,
)
from app.kamesan.models.stock import StockTransfer, StockTransferItem, StockTransferStatus


# ==========================================
# 測試資料庫設定
# ==========================================
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "fastapidemo_db", "fastapidemo_test_db"
).replace("mysql+pymysql://", "mysql+aiomysql://")


# 全域共享的引擎和 session factory
_shared_engine = None
_shared_session_factory = None
_tables_created = False


async def ensure_tables_created():
    """確保表格已建立（只在第一次呼叫時建立）"""
    global _shared_engine, _shared_session_factory, _tables_created

    if _shared_engine is None:
        _shared_engine = create_async_engine(
            TEST_DATABASE_URL,
            echo=False,
            poolclass=NullPool,
        )

    if not _tables_created:
        async with _shared_engine.begin() as conn:
            # 先清理所有表格
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            # 重新建立表格
            await conn.run_sync(SQLModel.metadata.create_all)
        _tables_created = True

    if _shared_session_factory is None:
        _shared_session_factory = async_sessionmaker(
            bind=_shared_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _shared_engine, _shared_session_factory


# ==========================================
# Session Scope Event Loop
# ==========================================
@pytest.fixture(scope="session")
def event_loop():
    """為整個測試 session 建立一個 event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==========================================
# Session Scope Database Setup
# ==========================================
@pytest_asyncio.fixture(scope="session")
async def db_setup():
    """
    Session 級別的資料庫設定

    在所有測試開始前建立表格，
    在所有測試結束後刪除表格。
    """
    engine, session_factory = await ensure_tables_created()

    yield engine, session_factory

    # 清理表格
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    # 關閉引擎
    await engine.dispose()

    # 重置全域變數
    global _shared_engine, _shared_session_factory, _tables_created
    _shared_engine = None
    _shared_session_factory = None
    _tables_created = False


# ==========================================
# Function Scope Fixtures
# ==========================================
@pytest_asyncio.fixture(scope="function")
async def session(db_setup) -> AsyncGenerator[AsyncSession, None]:
    """
    提供測試用資料庫 Session

    每個測試使用獨立的 Session，共用 session 級別的引擎。
    測試結束後清理所有資料。
    """
    engine, session_factory = db_setup

    # 清理所有資料的表格列表（按照外鍵順序刪除）
    tables_to_clean = [
        "purchase_receipt_items",
        "purchase_receipts",
        "purchase_order_items",
        "purchase_orders",
        "stock_transfer_items",
        "stock_transfers",
        "stock_count_items",
        "stock_counts",
        "payments",
        "order_items",
        "orders",
        "inventory_transactions",
        "inventories",
        "sales_return_items",
        "sales_returns",
        "purchase_return_items",
        "purchase_returns",
        "product_combo_items",
        "product_combos",
        "product_labels",
        "product_variants",
        "volume_pricing_rules",
        "supplier_prices",
        "products",
        "coupons",
        "promotions",
        "customers",
        "customer_levels",
        "stores",
        "warehouses",
        "categories",
        "units",
        "tax_types",
        "suppliers",
        "users",
        "roles",
        "report_schedules",
        "report_templates",
        "report_executions",
        "audit_logs",
        "numbering_sequences",
        "numbering_rules",
        "system_parameters",
        "shifts",
        "invoices",
    ]

    # 測試前清理數據
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables_to_clean:
            try:
                await conn.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    # 建立 session
    session = session_factory()
    try:
        yield session
        # 正常結束時嘗試 commit
        try:
            await session.commit()
        except Exception:
            pass
    except Exception:
        # 發生例外時嘗試 rollback
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        # 無論如何都要關閉 session
        try:
            await session.close()
        except Exception:
            pass

    # 測試後清理數據
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables_to_clean:
            try:
                await conn.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    提供測試用 HTTP 客戶端

    覆寫 app 的 database session dependency，
    使 API 測試也使用測試資料庫。
    """
    # 覆寫 database session dependency
    async def override_session():
        yield session

    app.dependency_overrides[get_async_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清除覆寫
    app.dependency_overrides.clear()


# ==========================================
# 使用者相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_role(session: AsyncSession) -> Role:
    """建立測試角色"""
    role = Role(
        code="TEST_ROLE",
        name="測試角色",
        description="用於測試的角色",
        permissions="test.read,test.write",
    )
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_user(session: AsyncSession, test_role: Role) -> User:
    """建立測試使用者"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="測試使用者",
        phone="0912345678",
        role_id=test_role.id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession) -> User:
    """建立管理員使用者"""
    # 建立管理員角色
    admin_role = Role(
        code="ADMIN",
        name="系統管理員",
        permissions="all",
    )
    session.add(admin_role)
    await session.flush()

    # 建立管理員使用者
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="系統管理員",
        is_superuser=True,
        role_id=admin_role.id,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """
    取得認證 Headers

    使用管理員帳號登入並取得 Token。
    """
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={
            "username": "admin",
            "password": "admin123",
        },
    )

    if response.status_code != 200:
        pytest.skip(f"無法取得認證 Token: {response.status_code} - {response.text}")

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 商品相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_unit(session: AsyncSession) -> Unit:
    """建立測試單位"""
    unit = Unit(code="PCS", name="個")
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


@pytest_asyncio.fixture
async def test_tax_type(session: AsyncSession) -> TaxType:
    """建立測試稅別"""
    tax_type = TaxType(code="TAX5", name="應稅5%", rate=Decimal("0.05"))
    session.add(tax_type)
    await session.commit()
    await session.refresh(tax_type)
    return tax_type


@pytest_asyncio.fixture
async def test_category(session: AsyncSession) -> Category:
    """建立測試類別"""
    category = Category(
        code="TEST_CAT",
        name="測試類別",
        level=1,
        sort_order=1,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_supplier(session: AsyncSession) -> Supplier:
    """建立測試供應商"""
    supplier = Supplier(
        code="SUP001",
        name="測試供應商",
        contact_name="聯絡人",
        phone="02-12345678",
        email="supplier@example.com",
        tax_id="12345678",
    )
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return supplier


@pytest_asyncio.fixture
async def test_product(
    session: AsyncSession,
    test_category: Category,
    test_unit: Unit,
    test_tax_type: TaxType,
    test_supplier: Supplier,
) -> Product:
    """建立測試商品"""
    product = Product(
        code="P001",
        barcode="4710000000001",
        name="測試商品",
        cost_price=Decimal("50.00"),
        selling_price=Decimal("100.00"),
        min_stock=10,
        max_stock=100,
        category_id=test_category.id,
        unit_id=test_unit.id,
        tax_type_id=test_tax_type.id,
        supplier_id=test_supplier.id,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


# ==========================================
# 倉庫與門市 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_warehouse(session: AsyncSession) -> Warehouse:
    """建立測試倉庫"""
    warehouse = Warehouse(
        code="WH001",
        name="測試倉庫",
        address="測試地址",
    )
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)
    return warehouse


@pytest_asyncio.fixture
async def test_warehouse2(session: AsyncSession) -> Warehouse:
    """建立第二個測試倉庫"""
    warehouse = Warehouse(
        code="WH002",
        name="測試倉庫2",
        address="測試地址2",
    )
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)
    return warehouse


@pytest_asyncio.fixture
async def test_store(session: AsyncSession, test_warehouse: Warehouse) -> Store:
    """建立測試門市"""
    store = Store(
        code="ST001",
        name="測試門市",
        address="門市地址",
        phone="02-87654321",
        warehouse_id=test_warehouse.id,
    )
    session.add(store)
    await session.commit()
    await session.refresh(store)
    return store


# ==========================================
# 客戶相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_customer_level(session: AsyncSession) -> CustomerLevel:
    """建立測試客戶等級"""
    level = CustomerLevel(
        code="NORMAL",
        name="一般會員",
        discount_rate=Decimal("0.00"),
        min_spending=Decimal("0.00"),
    )
    session.add(level)
    await session.commit()
    await session.refresh(level)
    return level


@pytest_asyncio.fixture
async def test_customer(
    session: AsyncSession,
    test_customer_level: CustomerLevel,
) -> Customer:
    """建立測試客戶"""
    customer = Customer(
        code="C001",
        name="測試客戶",
        phone="0911111111",
        email="customer@example.com",
        birthday=date(1990, 1, 1),
        level_id=test_customer_level.id,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


# ==========================================
# 庫存 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_inventory(
    session: AsyncSession,
    test_product: Product,
    test_warehouse: Warehouse,
) -> Inventory:
    """建立測試庫存"""
    inventory = Inventory(
        product_id=test_product.id,
        warehouse_id=test_warehouse.id,
        quantity=100,
        reserved_quantity=0,
    )
    session.add(inventory)
    await session.commit()
    await session.refresh(inventory)
    return inventory


# ==========================================
# 訂單相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_order(
    session: AsyncSession,
    test_store: Store,
    test_customer: Customer,
    test_product: Product,
    admin_user: User,
) -> Order:
    """建立測試訂單"""
    order = Order(
        order_number="ORD20240101001",
        store_id=test_store.id,
        customer_id=test_customer.id,
        status=OrderStatus.COMPLETED,
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        created_by=admin_user.id,
    )
    session.add(order)
    await session.flush()

    # 訂單明細
    order_item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        product_name=test_product.name,
        quantity=1,
        unit_price=Decimal("100.00"),
        subtotal=Decimal("100.00"),
        tax_rate=Decimal("0.05"),
        tax_amount=Decimal("5.00"),
    )
    session.add(order_item)

    # 付款
    payment = Payment(
        order_id=order.id,
        payment_method=PaymentMethod.CASH,
        amount=Decimal("105.00"),
        status=PaymentStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    session.add(payment)

    await session.commit()
    await session.refresh(order)
    return order


# ==========================================
# 促銷相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_promotion(session: AsyncSession) -> Promotion:
    """建立測試促銷"""
    now = datetime.now(timezone.utc)
    promotion = Promotion(
        code="PROMO001",
        name="測試促銷",
        description="測試用促銷活動",
        promotion_type=PromotionType.PERCENTAGE,
        discount_value=Decimal("10.00"),
        min_purchase=Decimal("100.00"),
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
    )
    session.add(promotion)
    await session.commit()
    await session.refresh(promotion)
    return promotion


@pytest_asyncio.fixture
async def test_coupon(
    session: AsyncSession,
    test_customer: Customer,
) -> Coupon:
    """建立測試優惠券"""
    now = datetime.now(timezone.utc)
    coupon = Coupon(
        code="CPN001",
        name="測試優惠券",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("50.00"),
        min_purchase=Decimal("200.00"),
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        customer_id=test_customer.id,
    )
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)
    return coupon


# ==========================================
# 採購相關 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_purchase_order(
    session: AsyncSession,
    test_supplier: Supplier,
    test_warehouse: Warehouse,
    test_product: Product,
    admin_user: User,
) -> PurchaseOrder:
    """建立測試採購單"""
    po = PurchaseOrder(
        order_number="PO20240101001",
        supplier_id=test_supplier.id,
        warehouse_id=test_warehouse.id,
        order_date=date.today(),
        expected_date=date.today() + timedelta(days=7),
        status=PurchaseOrderStatus.PENDING,
        total_amount=Decimal("500.00"),
        created_by=admin_user.id,
    )
    session.add(po)
    await session.flush()

    # 採購單明細
    po_item = PurchaseOrderItem(
        purchase_order_id=po.id,
        product_id=test_product.id,
        quantity=10,
        unit_price=Decimal("50.00"),
    )
    session.add(po_item)

    await session.commit()
    await session.refresh(po)
    return po


# ==========================================
# 庫存調撥 Fixtures
# ==========================================
@pytest_asyncio.fixture
async def test_stock_transfer(
    session: AsyncSession,
    test_warehouse: Warehouse,
    test_warehouse2: Warehouse,
    test_product: Product,
    admin_user: User,
) -> StockTransfer:
    """建立測試庫存調撥"""
    transfer = StockTransfer(
        transfer_number="ST20240101001",
        source_warehouse_id=test_warehouse.id,
        destination_warehouse_id=test_warehouse2.id,
        transfer_date=date.today(),
        status=StockTransferStatus.PENDING,
        created_by=admin_user.id,
    )
    session.add(transfer)
    await session.flush()

    # 調撥明細
    transfer_item = StockTransferItem(
        stock_transfer_id=transfer.id,
        product_id=test_product.id,
        quantity=10,
    )
    session.add(transfer_item)

    await session.commit()
    await session.refresh(transfer)
    return transfer
