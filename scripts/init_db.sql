-- ============================================
-- FastAPI Demo - 資料庫初始化腳本
-- ============================================
-- 此腳本在 MySQL 容器首次啟動時自動執行
-- 用於設定資料庫字元集和時區
-- ============================================

-- 設定資料庫字元集
ALTER DATABASE fastapidemo_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 設定時區為台北時間
SET GLOBAL time_zone = '+08:00';
