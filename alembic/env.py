"""
Alembic 環境配置

設定資料庫遷移的執行環境，
使用同步模式執行遷移。
"""

import sys
from pathlib import Path

# 確保 app 模組可被匯入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from sqlmodel import SQLModel

# 匯入所有模型以確保 metadata 包含所有表定義
from app.kamesan.models import (
    Category,
    Coupon,
    Customer,
    CustomerLevel,
    Inventory,
    InventoryTransaction,
    Order,
    OrderItem,
    Payment,
    Product,
    Promotion,
    Role,
    Store,
    Supplier,
    TaxType,
    Unit,
    User,
    Warehouse,
)
from app.kamesan.core.config import settings

# Alembic Config 物件
config = context.config

# 設定 SQLAlchemy URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 設定 logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目標 metadata（用於 autogenerate）
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    離線模式執行遷移

    不需要資料庫連線，直接產生 SQL 腳本。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    線上模式執行遷移

    連線到資料庫並執行遷移（同步模式）。
    """
    # 使用同步引擎進行遷移
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 比較欄位類型變更
            compare_server_default=True,  # 比較預設值變更
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
