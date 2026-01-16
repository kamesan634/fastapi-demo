# ============================================
# FastAPI Demo - Makefile
# ============================================
# 常用指令集合，簡化開發流程
#
# 使用方式:
#   make help      - 顯示所有可用指令
#   make run       - 啟動開發伺服器
#   make test      - 執行測試
# ============================================

.PHONY: help run build up down logs test lint format migrate seed clean

# 預設目標
.DEFAULT_GOAL := help

# ==========================================
# 幫助訊息
# ==========================================
help:
	@echo "FastAPI Demo - 可用指令"
	@echo ""
	@echo "Docker 相關:"
	@echo "  make build      - 建置 Docker 映像檔"
	@echo "  make up         - 啟動所有服務"
	@echo "  make down       - 停止所有服務"
	@echo "  make logs       - 查看服務日誌"
	@echo "  make restart    - 重新啟動所有服務"
	@echo ""
	@echo "開發相關:"
	@echo "  make run        - 啟動開發伺服器（本機）"
	@echo "  make shell      - 進入 web 容器 shell"
	@echo ""
	@echo "資料庫相關:"
	@echo "  make migrate    - 執行資料庫遷移"
	@echo "  make makemigrations - 產生遷移檔案"
	@echo "  make seed       - 載入測試資料"
	@echo ""
	@echo "測試相關:"
	@echo "  make test       - 執行所有測試"
	@echo "  make test-cov   - 執行測試並產生覆蓋率報告"
	@echo "  make test-unit  - 只執行單元測試"
	@echo "  make test-api   - 只執行 API 測試"
	@echo ""
	@echo "程式碼品質:"
	@echo "  make lint       - 執行程式碼檢查"
	@echo "  make format     - 格式化程式碼"
	@echo "  make check      - 執行所有檢查（lint + test）"
	@echo ""
	@echo "清理相關:"
	@echo "  make clean      - 清理暫存檔案"
	@echo "  make clean-all  - 清理所有（含 Docker volumes）"

# ==========================================
# Docker 指令
# ==========================================
build:
	@echo "建置 Docker 映像檔..."
	docker-compose build

up:
	@echo "啟動所有服務..."
	docker-compose up -d

down:
	@echo "停止所有服務..."
	docker-compose down

logs:
	docker-compose logs -f

restart:
	@echo "重新啟動所有服務..."
	docker-compose restart

shell:
	docker-compose exec web bash

# ==========================================
# 開發指令
# ==========================================
run:
	@echo "啟動開發伺服器..."
	uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# ==========================================
# 資料庫指令
# ==========================================
migrate:
	@echo "執行資料庫遷移..."
	docker-compose exec web alembic upgrade head

makemigrations:
	@echo "產生遷移檔案..."
	@read -p "遷移訊息: " msg; \
	docker-compose exec web alembic revision --autogenerate -m "$$msg"

seed:
	@echo "載入測試資料..."
	docker-compose exec web python scripts/seed_data.py

# ==========================================
# 測試指令
# ==========================================
test:
	@echo "執行所有測試..."
	docker-compose exec web pytest

test-cov:
	@echo "執行測試並產生覆蓋率報告..."
	docker-compose exec web pytest --cov=app --cov-report=term-missing --cov-report=html

test-unit:
	@echo "執行單元測試..."
	docker-compose exec web pytest tests/unit -v

test-api:
	@echo "執行 API 測試..."
	docker-compose exec web pytest tests/api -v

# ==========================================
# 程式碼品質指令
# ==========================================
lint:
	@echo "執行程式碼檢查..."
	docker-compose exec web flake8 app tests
	docker-compose exec web mypy app

format:
	@echo "格式化程式碼..."
	docker-compose exec web black app tests
	docker-compose exec web isort app tests

check: lint test
	@echo "所有檢查完成！"

# ==========================================
# 清理指令
# ==========================================
clean:
	@echo "清理暫存檔案..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage 2>/dev/null || true

clean-all: clean down
	@echo "清理所有資料（含 Docker volumes）..."
	docker-compose down -v
	docker system prune -f
