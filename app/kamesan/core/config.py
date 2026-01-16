"""
應用程式配置模組

使用 Pydantic Settings 管理環境變數，
支援從 .env 檔案或系統環境變數讀取設定。

設定類別：
- 應用程式基本設定
- 資料庫連線設定
- Redis 快取設定
- JWT 認證設定
- CORS 跨域設定
- Celery 背景任務設定
- 日誌設定
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    應用程式設定類別

    所有設定值優先從環境變數讀取，
    若環境變數不存在則使用預設值。
    """

    # ==========================================
    # 應用程式基本設定
    # ==========================================
    APP_NAME: str = "FastAPI Demo"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"  # development / staging / production
    DEBUG: bool = True

    # API 版本前綴
    API_V1_PREFIX: str = "/api/v1"

    # 伺服器設定
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # ==========================================
    # 資料庫設定 (MySQL)
    # ==========================================
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "dev123"
    DB_NAME: str = "fastapidemo_db"

    @property
    def DATABASE_URL(self) -> str:
        """
        組合資料庫連線 URL

        回傳值:
            str: MySQL 連線字串，格式為
                 mysql+pymysql://user:password@host:port/database
        """
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    # ==========================================
    # Redis 設定
    # ==========================================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        """
        組合 Redis 連線 URL

        回傳值:
            str: Redis 連線字串
        """
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==========================================
    # JWT 認證設定
    # ==========================================
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # Access Token 有效期 (分鐘)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh Token 有效期 (天)

    # ==========================================
    # CORS 跨域設定
    # ==========================================
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """
        解析 CORS 允許的來源網域列表

        回傳值:
            List[str]: 允許的網域列表
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ==========================================
    # Celery 背景任務設定
    # ==========================================
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ==========================================
    # 日誌設定
    # ==========================================
    LOG_LEVEL: str = "DEBUG"

    # ==========================================
    # 分頁設定
    # ==========================================
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ==========================================
    # Pydantic Settings 配置
    # ==========================================
    model_config = SettingsConfigDict(
        env_file=".env",  # 從 .env 檔案讀取
        env_file_encoding="utf-8",
        case_sensitive=True,  # 環境變數區分大小寫
        extra="ignore",  # 忽略未定義的環境變數
    )


@lru_cache()
def get_settings() -> Settings:
    """
    取得應用程式設定實例

    使用 lru_cache 裝飾器確保設定只會載入一次，
    提升效能並確保設定一致性。

    回傳值:
        Settings: 應用程式設定實例
    """
    return Settings()


# 匯出設定實例供全域使用
settings = get_settings()
