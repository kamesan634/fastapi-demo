# ============================================
# FastAPI Demo - Dockerfile
# ============================================
# 使用 Python 3.12 官方映像檔
# 建置說明：
#   1. 安裝系統依賴
#   2. 安裝 Python 依賴套件
#   3. 複製應用程式碼
#   4. 設定啟動指令
# ============================================

FROM python:3.12-slim

# 設定環境變數
# PYTHONDONTWRITEBYTECODE: 不產生 .pyc 檔案
# PYTHONUNBUFFERED: 不緩衝輸出，方便即時查看日誌
# PYTHONPATH: 設定 Python 模組搜尋路徑
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
# - curl: 健康檢查用
# - gcc, default-libmysqlclient-dev: MySQL 客戶端編譯用
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴清單並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立非 root 使用者並切換
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露服務埠
EXPOSE 8002

# 預設啟動指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
