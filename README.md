# 龜三的ERP Demo - FastAPI

![CI](https://github.com/kamesan634/fastapi-demo/actions/workflows/ci.yml/badge.svg)

基於 Python 3.12 + FastAPI DEMO用的零售業 ERP 系統後端 API。

## 技能樹 請點以下技能

| 技能 | 版本 | 說明 |
|------|------|------|
| Python | 3.12 | 程式語言 |
| FastAPI | 0.109 | 核心框架 |
| SQLModel | 0.0.14 | ORM 框架 (SQLAlchemy + Pydantic) |
| MySQL | 8.4 | 資料庫 |
| Redis | 7 | 快取服務 |
| Celery | 5.3 | 背景任務 |
| Alembic | 1.13 | 資料庫遷移 |
| JWT (python-jose) | 3.3 | Token 認證 |
| Uvicorn | 0.27 | ASGI Server |
| Docker | - | 容器化佈署 |
| pytest | 8.0 | 測試框架 |

## 功能模組

- **auth** - 認證管理（JWT Token、Token 刷新、密碼變更）
- **accounts** - 帳號管理（使用者、角色、門市、倉庫）
- **products** - 商品管理（商品、分類、單位、稅別）
- **suppliers** - 供應商管理（供應商）
- **customers** - 客戶管理（會員、會員等級）
- **inventory** - 庫存管理（庫存查詢、調整、異動記錄、低庫存警示）
- **sales** - 銷售管理（訂單、訂單明細、付款）
- **promotions** - 促銷管理（促銷活動、優惠券）

## 快速開始

### 環境需求

- Docker & Docker Compose
- 或 Python 3.12 + MySQL 8.4 + Redis

### 使用 Docker 佈署（推薦）

```bash
# 啟動所有服務
docker-compose up -d --build

# 執行資料庫遷移
docker-compose exec web alembic upgrade head

# 載入測試資料
docker-compose exec web python scripts/seed_data.py

# 查看日誌
docker-compose logs -f web

# 停止服務
docker-compose down
```

### 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行資料庫遷移
alembic upgrade head

# 啟動開發伺服器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

## Port

| 服務 | Port | 說明 |
|------|------|------|
| FastAPI | 8002 | REST API 服務 |
| MySQL | 3302 | 資料庫 |
| Redis | 6382 | 快取服務 |

## API 文件

啟動服務後，訪問 Swagger UI：

- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **OpenAPI JSON**: http://localhost:8002/openapi.json

主要端點：

| 模組 | 端點 | 說明 |
|------|------|------|
| 認證 | POST /api/v1/auth/login | 登入 |
| 認證 | POST /api/v1/auth/refresh | Token 刷新 |
| 認證 | POST /api/v1/auth/change-password | 變更密碼 |
| 使用者 | /api/v1/users | 使用者 CRUD |
| 角色 | /api/v1/roles | 角色 CRUD |
| 門市 | /api/v1/stores | 門市 CRUD |
| 倉庫 | /api/v1/warehouses | 倉庫 CRUD |
| 分類 | /api/v1/categories | 分類 CRUD |
| 單位 | /api/v1/units | 單位 CRUD |
| 稅別 | /api/v1/tax-types | 稅別 CRUD |
| 商品 | /api/v1/products | 商品 CRUD |
| 供應商 | /api/v1/suppliers | 供應商 CRUD |
| 會員等級 | /api/v1/customer-levels | 會員等級 CRUD |
| 會員 | /api/v1/customers | 會員 CRUD |
| 庫存 | /api/v1/inventories | 庫存查詢、調整 |
| 訂單 | /api/v1/orders | 訂單 CRUD |
| 促銷 | /api/v1/promotions | 促銷活動 CRUD |
| 優惠券 | /api/v1/coupons | 優惠券 CRUD |

## 測試資訊

### 測試帳號

| 帳號 | 密碼 | 角色 | 說明 |
|------|------|------|------|
| admin | admin123 | 系統管理員 | 擁有所有權限 |
| manager | manager123 | 店長 | 門市管理、訂單、庫存權限 |
| cashier1 | cashier123 | 收銀員 | POS 收銀、商品查詢權限 |
| warehouse | warehouse123 | 倉管人員 | 庫存管理、商品查詢權限 |

### 重置測試資料

```bash
# 停止服務並刪除 volumes
docker-compose down -v

# 重新啟動並初始化
docker-compose up -d --build
docker-compose exec web alembic upgrade head
docker-compose exec web python scripts/seed_data.py
```

## 執行測試

### 單元測試

```bash
# 執行所有測試
docker-compose exec web pytest

# 執行並產生覆蓋率報告
docker-compose exec web pytest --cov=app --cov-report=html

# 只執行單元測試
docker-compose exec web pytest tests/unit

# 只執行 API 測試
docker-compose exec web pytest tests/api
```

### 測試覆蓋範圍

| 模組 | 測試類別 | 測試項目 |
|------|----------|----------|
| 認證 | test_auth.py | 登入、Token 刷新、變更密碼、驗證錯誤處理 |
| 使用者 | test_users.py | CRUD、權限檢查 |
| 安全性 | test_security.py | 密碼雜湊、JWT Token |

## API 使用範例

### 登入取得 Token

```bash
curl -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

回應：
```json
{
  "success": true,
  "message": "登入成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "name": "系統管理員"
    }
  }
}
```

### 查詢商品列表

```bash
curl -X GET http://localhost:8002/api/v1/products \
  -H "Authorization: Bearer {YOUR_TOKEN}"
```

### 建立訂單

```bash
curl -X POST http://localhost:8002/api/v1/orders \
  -H "Authorization: Bearer {YOUR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": 1,
    "customer_id": 1,
    "items": [
      {"product_id": 1, "quantity": 2, "unit_price": 199.00}
    ]
  }'
```

## 專案結構

```
fastapi-demo/
├── docker-compose.yml          # Docker Compose 配置
├── Dockerfile                  # Docker 映像配置
├── Makefile                    # Make 指令
├── requirements.txt            # Python 依賴
├── alembic.ini                 # Alembic 配置
├── alembic/
│   ├── env.py                  # Alembic 環境配置
│   └── versions/               # 遷移版本檔案
├── scripts/
│   ├── init_db.sql             # 資料庫初始化 SQL
│   └── seed_data.py            # Seed Data 腳本
├── app/
│   ├── main.py                 # FastAPI 應用程式進入點
│   ├── api/
│   │   └── v1/
│   │       ├── router.py       # API 路由彙整
│   │       └── endpoints/      # API 端點實作
│   ├── core/
│   │   ├── config.py           # 應用程式設定
│   │   ├── database.py         # 資料庫連線
│   │   ├── security.py         # JWT 與密碼
│   │   └── deps.py             # 依賴注入
│   ├── models/                 # SQLModel 模型
│   ├── schemas/                # Pydantic Schema
│   └── tasks/                  # Celery 背景任務
└── tests/
    ├── conftest.py             # pytest fixtures
    ├── api/                    # API 測試
    └── unit/                   # 單元測試
```

## Celery 背景任務

### 可用任務

| 任務 | 說明 |
|------|------|
| check_low_stock | 檢查低庫存商品並發送通知 |
| send_low_stock_notification | 發送低庫存警告通知 |
| update_stock_after_order | 訂單完成後更新庫存 |
| send_order_confirmation | 發送訂單確認通知 |
| generate_daily_sales_report | 產生每日銷售報表 |

## 資料庫連線

### Docker 環境

- Host: `localhost`
- Port: `3302`
- Database: `fastapidemo_db`
- Username: `root`
- Password: `dev123`

```bash
# 使用 MySQL 客戶端連線
mysql -h 127.0.0.1 -P 3302 -uroot -pdev123 fastapidemo_db

# 或進入 Docker 容器
docker-compose exec db mysql -uroot -pdev123 fastapidemo_db
```

## 健康檢查

```bash
# 檢查應用程式健康狀態
curl http://localhost:8002/health
```

## 常見問題

### Q: Docker 啟動失敗？

1. 確認 Docker 服務已啟動
2. 確認 Ports 8002, 3302, 6382 未被佔用
3. 查看日誌：`docker-compose logs`

### Q: 登入失敗？

1. 確認使用正確的帳號密碼
2. 確認已執行 seed_data.py 建立測試帳號
3. 重置資料：`docker-compose down -v` 後重新初始化

### Q: 測試失敗？

1. 確認使用 Python 3.12
2. 測試使用 SQLite 內嵌資料庫，無需外部依賴
3. 執行：`docker-compose exec web pytest -v`

## License

MIT License
我一開始以為是Made In Taiwan 咧！(羞
