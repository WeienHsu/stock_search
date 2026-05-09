# Stock Intelligence

Streamlit + Python 的個人股票分析工具，支援台股 / 美股 ticker 分析、策略訊號、回測、風控、自選清單、新聞情緒、價格警示與常駐排程。

## 目前功能

- Dashboard：K 線、MA、KD、MACD、Bias、策略買賣訊號、新聞情緒。
- Market Overview：TAIEX/GTSM、USD/TWD、法人買賣超、TAIFEX 外資期貨未平倉、CNN Fear & Greed、MMFI、台股估值與融資融券。
- Scanner：掃描自選清單，顯示買進 / 賣出訊號狀態。
- Backtest：策略回測、勝率、Sharpe、最大回撤等指標。
- Risk：ATR 停損與部位控管。
- Alerts：價格警示 CRUD、Inbox fallback、排程執行紀錄。
- Notifications：Email SMTP、Telegram Bot、Inbox fallback。
- Scheduler：APScheduler worker，支援價格警示、每日策略掃描、週報 placeholder。
- Cache：依市場交易時段調整價格 / 新聞快取 TTL。
- Docker：`app` + `worker` 雙服務常駐，資料持久化保存。

## 環境設定

建立 `.env`：

```bash
cp .env.example .env
```

產生加密用 key，填入 `.env` 的 `APP_SECRET_KEY`：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

最小 `.env` 範例：

```env
FINNHUB_API_KEY=your_key_here
STORAGE_BACKEND=sqlite
FINNHUB_KEY_MODE=global
APP_SECRET_KEY=your_generated_fernet_key
ENABLE_STREAMLIT_SCHEDULER=0
```

`APP_SECRET_KEY` 請固定保存；更換後會無法解密已儲存的 API key、SMTP password、Telegram token。

## 本機開發啟動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

若要本機常駐排程，另開一個 terminal：

```bash
source .venv/bin/activate
python -m src.scheduler.worker
```

單 process 測試也可使用：

```bash
ENABLE_STREAMLIT_SCHEDULER=1 streamlit run app.py
```

長期使用建議用獨立 worker 或 Docker Compose。

## Docker 常駐啟動

```bash
docker compose up -d --build
```

開啟：

```text
http://localhost:8501
```

查看狀態：

```bash
docker compose ps
docker compose logs -f worker
```

手動觸發一次價格警示掃描：

```bash
docker compose exec worker python -c "from src.scheduler.jobs.price_alerts import run_price_alerts; print(run_price_alerts())"
```

Docker Compose 會建立：

- `app`：Streamlit UI
- `worker`：APScheduler 常駐排程
- `stock_data` volume：保存 `/app/data` 內所有 DB、使用者設定、警示、cache

## Email 通知設定

進入 App 的「設定」→「通知設定」。

Gmail 範例：

```text
啟用 Email: 勾選
收件 Email: 你的收件信箱
SMTP host: smtp.gmail.com
SMTP port: 587
SMTP username: 你的完整 Gmail
TLS: 勾選
SMTP password / app password: Gmail App Password
價格警示通道: email, inbox
```

儲存後按「傳送測試通知」。若 Email 或 Telegram 失敗，系統仍會寫入「警示」頁的 Inbox。

## Telegram 通知設定

進入「設定」→「通知設定」：

```text
啟用 Telegram: 勾選
Telegram chat_id: 你的 chat id
Telegram bot token: BotFather 產生的 token
價格警示通道: telegram, inbox
```

儲存後可用「傳送測試通知」驗證。

## 價格警示驗證

1. 進入「警示」頁。
2. 新增一筆容易觸發的警示，例如 `TSLA >= 1`。
3. 手動執行：

```bash
python -c "from src.scheduler.jobs.price_alerts import run_price_alerts; print(run_price_alerts())"
```

Docker 模式：

```bash
docker compose exec worker python -c "from src.scheduler.jobs.price_alerts import run_price_alerts; print(run_price_alerts())"
```

4. 回到「警示」頁確認：

- alert 顯示已觸發
- Inbox 有訊息
- 排程紀錄有 `price_alerts`

## 測試

```bash
pytest -q
```

本機提交前建議安裝 pre-commit hooks：

```bash
pre-commit install
pre-commit run --all-files
```

目前 hooks 會檢查 YAML、檔尾換行、尾端空白，並執行 `python scripts/check_contrast.py` 驗證 UI token 對比度。

目前主要測試涵蓋：

- 指標與策略
- 回測與風控
- cache TTL
- 資料源 probe parser
- alert / inbox / scheduler repos
- notification fallback
- price alert job

## 資料備份

Docker volume 備份：

```bash
docker run --rm -v stock_search_stock_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/stock_data_backup.tgz -C /data .
```

還原：

```bash
docker run --rm -v stock_search_stock_data:/data -v "$PWD":/backup alpine \
  sh -c "cd /data && tar xzf /backup/stock_data_backup.tgz"
```

## 重要文件

- `docs/improved_Plan_20260502.md`：分 phase 改進計畫與完成紀錄。
- `docs/data_source_mapping_P0_5.md`：TWSE / TPEX / TAIFEX / CNN / MMFI 資料源驗證結果。
- `docs/docker_deployment.md`：Docker 常駐部署細節。
