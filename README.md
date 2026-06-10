# Stock Intelligence — 台美股監測終端

追蹤台股 / 美股的個人投資監測工具：**React 專業終端介面 + FastAPI + Python 分析核心**，
支援即時報價、K 線與技術指標、策略買賣訊號、到價警示與常駐自動化監測。

```
web/     React 19 + TypeScript + Vite + lightweight-charts（終端 UI）
server/  FastAPI 薄 API 層（/api/*）
src/     Python 核心：資料抓取、指標、策略、掃描、警示、排程、通知
```

## 功能

- **即時報價**：台股走 TWSE MIS API（盤中即時）、美股走 yfinance；自選清單跳動閃色。
- **K 線終端**：lightweight-charts 多 pane（K 線 + MA5/10/20/60 + 量、MACD、KD），
  策略買賣訊號 marker、十字線 OHLC、紅漲綠跌 / 綠漲紅跌切換。
- **到價警示**：表單或「圖表點價」建立，警示線直接畫在圖上；worker 常駐監測，
  觸發後寫入事件並透過 Email / Telegram / LINE / 站內通知送達。
- **策略掃描**：對整個自選清單跑策略（Strategy D / KD / Bias），
  顯示買賣訊號狀態、趨勢、多頭排列分數、支撐區。
- **大盤狀態列**：加權指數、S&P 500、NASDAQ、USD/TWD、CNN Fear & Greed、委買賣比。
- **自動化排程**（worker）：盤中價格警示、台美股每日策略掃描通知、台股籌碼快照。
- **回測引擎**：策略勝率 / Sharpe / 最大回撤（`src/backtest`，目前為程式庫層）。

## 環境設定

```bash
cp .env.example .env
```

產生加密用 key 填入 `APP_SECRET_KEY`（保存通知憑證用，請固定保存）：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

最小 `.env`：

```env
STORAGE_BACKEND=sqlite
APP_SECRET_KEY=your_generated_fernet_key
```

## 本機開發

```bash
# 1. 後端
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8700

# 2. 前端（另開 terminal）
cd web && npm install && npm run dev   # http://localhost:5173

# 3. 常駐排程 worker（另開 terminal，警示／每日掃描需要）
python -m src.scheduler.worker
```

API 文件：<http://127.0.0.1:8700/docs>（FastAPI 自動生成）。

## 正式部署（Docker）

```bash
docker compose up -d --build
```

- `api`：uvicorn 同時服務 `/api/*` 與打包後的前端（<http://localhost:8700>）。
- `worker`：APScheduler 常駐排程（價格警示每 15 分鐘、每日掃描台股 14:10 / 美股 05:10、
  籌碼快照 17:30）。

## 資料庫 Migration（Postgres / Supabase）

`STORAGE_BACKEND=postgres` 時，`migrations/*.sql` 透過下列腳本套用
（依檔名排序，已套用的自動跳過，記錄於 `schema_migrations` 表）：

```bash
python scripts/apply_migrations.py
```

> **執行順序**：資料表是第一次連線時 `CREATE TABLE IF NOT EXISTS` 自動建立的，
> `enable_rls.sql` 只對執行當下已存在的表啟用 RLS。請先啟動 App 讓資料表建立，
> 再執行 migration。

## 測試

```bash
pytest -q          # Python（API、指標、策略、排程、repo）
cd web && npm run build   # TypeScript 型別檢查 + 打包
```

## 架構說明

詳見 `docs/refactor_evaluation_20260611.md`（評估與重構決策，本機文件）。
