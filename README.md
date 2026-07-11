# Stock Intelligence — 台美股監測終端

追蹤台股 / 美股的個人投資監測工具:**React 終端介面 + FastAPI + Python 分析核心**。
提供即時報價、K 線與技術指標、策略買賣訊號(含早期背離訊號與乖離率副圖)、
自選清單策略掃描、到價警示,以及常駐排程自動通知(Email / Telegram / LINE / 站內)。

```
web/     React 19 + TypeScript + Vite + lightweight-charts(終端 UI)
server/  FastAPI 薄 API 層(/api/*)
src/     Python 核心:資料抓取、指標、策略、掃描、警示、排程、通知
```

## 快速開始(本機開發)

### 1. 環境設定

```bash
cp .env.example .env
```

最小 `.env`(其餘選項見 `.env.example` 內註解):

```env
STORAGE_BACKEND=sqlite
APP_SECRET_KEY=your_generated_fernet_key
```

`APP_SECRET_KEY` 用於加密保存通知憑證,產生後請固定不要更換:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 啟動服務

```bash
# 後端 API
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8700

# 前端(另開 terminal)
cd web && npm install && npm run dev   # http://localhost:5173

# 常駐排程 worker(另開 terminal;到價警示、每日掃描通知需要)
python -m src.scheduler.worker
```

API 文件:<http://127.0.0.1:8700/docs>(FastAPI 自動生成)。

## 正式部署(Docker)

需先備妥 `.env`(同上),再:

```bash
docker compose up -d --build
```

- `api`:uvicorn 同時服務 `/api/*` 與打包後的前端,<http://localhost:8700>。
- `worker`:APScheduler 常駐排程——價格警示每 15 分鐘、每日策略掃描台股 14:10 /
  美股 05:10、台股籌碼快照 17:30。
- 兩個容器共用 `stock_data` volume(SQLite DB 與快取),健康檢查走 `/api/health`。

### Postgres / Supabase(選用)

`.env` 設 `STORAGE_BACKEND=postgres` 並填 `DATABASE_URL`。
`migrations/*.sql` 以下列腳本套用(依檔名排序、已套用自動跳過,記錄於
`schema_migrations` 表):

```bash
python scripts/apply_migrations.py
```

> **執行順序**:資料表由 App 第一次連線時自動建立,`enable_rls.sql` 只對已存在的表
> 啟用 RLS。請先啟動 App 讓資料表建立,再執行 migration。

## 測試

```bash
pytest -q                 # Python(API、指標、策略、排程、repo)
cd web && npm run build   # TypeScript 型別檢查 + 打包
```
