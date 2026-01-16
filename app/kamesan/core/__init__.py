"""
核心模組

包含：
- config: 應用程式配置
- database: 資料庫連線
- security: 安全性功能（JWT、密碼雜湊）
- deps: 依賴注入
- logging: 日誌配置
"""

from app.kamesan.core.config import settings

__all__ = ["settings"]
