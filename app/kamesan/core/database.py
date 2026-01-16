"""
資料庫連線模組

使用 SQLModel 建立資料庫連線與 Session 管理。
支援非同步操作，提供依賴注入用的 Session 工廠。

功能：
- 建立資料庫引擎
- 管理連線池
- 提供 Session 依賴注入
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.kamesan.core.config import settings

# ==========================================
# 建立非同步資料庫引擎
# ==========================================
# 使用 aiomysql 作為非同步 MySQL 驅動
# 連線字串格式: mysql+aiomysql://user:password@host:port/database
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "mysql+pymysql://", "mysql+aiomysql://"
)

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,  # 開發模式下輸出 SQL 語句
    pool_size=10,  # 連線池大小
    max_overflow=20,  # 超過 pool_size 時可額外建立的連線數
    pool_pre_ping=True,  # 連線前先 ping 確認連線有效
    pool_recycle=3600,  # 連線回收時間（秒）
)

# ==========================================
# 建立非同步 Session 工廠
# ==========================================
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit 後不過期物件，避免額外查詢
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    取得非同步資料庫 Session

    使用 async generator 確保 Session 在請求結束後正確關閉。
    透過 FastAPI 的依賴注入系統使用。

    產生值:
        AsyncSession: 非同步資料庫 Session

    使用範例:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化資料庫

    建立所有 SQLModel 定義的資料表。
    注意：正式環境應使用 Alembic 進行資料庫遷移。

    此函數僅用於開發環境快速建立資料表。
    """
    async with engine.begin() as conn:
        # 建立所有資料表
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """
    關閉資料庫連線

    應在應用程式關閉時呼叫，釋放所有連線資源。
    """
    await engine.dispose()
