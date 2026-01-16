"""
FastAPI 應用程式主程式

這是應用程式的進入點，負責：
- 初始化 FastAPI 應用
- 設定中介軟體（CORS、日誌等）
- 註冊 API 路由
- 設定事件處理器（啟動、關閉）
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.kamesan.api.v1.router import api_router
from app.kamesan.core.config import settings
from app.kamesan.core.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    應用程式生命週期管理

    在應用程式啟動時執行初始化，
    在應用程式關閉時執行清理。
    """
    # 啟動時執行
    print(f"正在啟動 {settings.APP_NAME}...")

    # 注意：正式環境應使用 Alembic 進行資料庫遷移
    # await init_db()

    print(f"{settings.APP_NAME} 啟動完成！")
    print(f"API 文件: http://{settings.HOST}:{settings.PORT}/docs")

    yield  # 應用程式運行中

    # 關閉時執行
    print(f"正在關閉 {settings.APP_NAME}...")
    await close_db()
    print(f"{settings.APP_NAME} 已關閉。")


# ==========================================
# 建立 FastAPI 應用程式
# ==========================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## FastAPI Demo - 零售業簡易 ERP 系統

    這是一個展示用的零售業 ERP 系統 API，包含以下功能：

    ### 模組功能

    * **認證模組** - JWT 登入、登出、Token 刷新
    * **使用者管理** - 使用者 CRUD、角色管理
    * **門市管理** - 門市與倉庫管理
    * **客戶管理** - 客戶與會員等級管理
    * **商品管理** - 商品、類別、單位、稅別管理
    * **庫存管理** - 庫存查詢、調整、異動記錄
    * **銷售管理** - 訂單建立、付款、退款
    * **促銷管理** - 促銷活動、優惠券管理

    ### 技術特色

    * FastAPI + SQLModel + MySQL
    * JWT 認證 + RBAC 權限控制
    * Celery 背景任務處理
    * Redis 快取
    * Docker Compose 容器化部署
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ==========================================
# 設定 CORS 中介軟體
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 全域異常處理器
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全域異常處理器

    捕捉所有未處理的異常，回傳統一格式的錯誤回應。
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "內部伺服器錯誤",
            "message": str(exc) if settings.DEBUG else "請聯繫系統管理員",
        },
    )


# ==========================================
# 註冊 API 路由
# ==========================================
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ==========================================
# 健康檢查端點
# ==========================================
@app.get("/health", tags=["健康檢查"])
async def health_check():
    """
    健康檢查端點

    用於 Docker 健康檢查和負載均衡器存活探測。

    回傳值:
        dict: 包含狀態和版本資訊
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["首頁"])
async def root():
    """
    API 首頁

    提供基本的 API 資訊和文件連結。
    """
    return {
        "message": f"歡迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }
