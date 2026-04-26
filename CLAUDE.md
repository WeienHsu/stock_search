# Stock Intelligence Dashboard — Project Rules

## 執行環境
- 虛擬環境：`source .venv/bin/activate`（所有指令必須在此環境下執行）
- Python 3.12+
- Streamlit (latest stable)
- macOS 本地開發

## 資料來源規範
- 股價數據：優先使用 `yfinance`
- 台股 ticker 一律加 `.TW` suffix（例如：`2330.TW`）
- 美股直接使用 ticker（例如：`TSLA`、`PLTR`）
- 市場情緒：Finnhub API，key 存於 `.env`（`FINNHUB_API_KEY`）
- 快取：初期使用 JSON / pickle 存於本地

## 架構原則
- 指標計算與信號邏輯必須透過 **Strategy Pattern** 解耦
- 每個策略模組（Strategy D、E、F...）需可獨立新增，不影響現有模組
- 所有指標參數必須可由側邊欄即時調整，不得 hardcode
- 資料存取一律以 **Repository Pattern** 封裝，初期用 JSON / pickle，
  介面設計需確保未來可無痛替換為 SQLite / PostgreSQL 或其他儲存方案
- 所有與「使用者身份」相關的邏輯（自選清單、偏好設定、風險額度）必須以
  `user_id` 為 key 隔離，初期 user_id 固定為 `"local"`，
  確保未來接入登入系統時不需要重構資料層

## 乖離率公式
Bias = (收盤價 - MA_n) / MA_n × 100%
預設 n=20，支援用戶切換 10 / 20 / 60

## UI 規範
- 風格：Minimalist（極簡）
- 配色：Morandi（莫蘭迪低飽和度色調）
- 所有指標面板需有獨立「顯示 / 關閉」開關

## 初期不實作、但架構需預留空間的功能
- 用戶登入 / 帳號系統（資料層已用 user_id 隔離，未來接入 Auth 不需重構）
- 資料庫（Repository Pattern 已封裝，未來替換不影響業務邏輯）
- Docker / 雲端部署
- 即時 WebSocket 串流（輪詢即可，未來可升級）

## 初期明確不包含
- 任何第三方 Auth 整合（Google OAuth、JWT 等）
- 多人即時協作功能
