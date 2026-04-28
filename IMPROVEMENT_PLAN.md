# Stock Intelligence Dashboard — 改進計劃（2026-04-28）

> Branch: `claude/improve-persistence-backtest-sTbZi`

---

## Issue 1｜Docker 部署持久化設計

### 現況說明

Streamlit **本身不提供任何持久化機制**——`st.session_state` 只存活於單一瀏覽器 Session，重新整理即清空，容器重啟後完全消失。

本專案的真正持久化層是 **Repository Pattern 封裝的檔案系統**：

| 資料類型 | 路徑 | 格式 | 存活條件 |
|----------|------|------|----------|
| 使用者資料（自選清單、偏好、風險設定） | `data/users/{user_id}/` | JSON | 只要宿主目錄掛載 |
| 價格快取 | `data/cache/prices/` | Pickle + .meta | 同上（TTL 6h 自動失效） |
| 新聞快取 | `data/cache/news/` | Pickle + .meta | 同上（TTL 1h 自動失效） |

### 問題根因

原 `Dockerfile` 只建立了 `RUN mkdir -p` 的目錄，**容器重啟後資料消失**，因為沒有掛載 Volume。

### 改進方案

新增 `docker-compose.yml`，使用 **Named Volume** 將三個資料目錄對映到宿主機：

```yaml
volumes:
  - stock_user_data:/app/data/users       # 使用者資料永久保存
  - stock_price_cache:/app/data/cache/prices
  - stock_news_cache:/app/data/cache/news
```

### 部署指令

```bash
# 首次啟動
cp .env.example .env          # 填入 FINNHUB_API_KEY
docker compose up -d          # 建置映像 + 背景啟動

# 更新版本（資料不受影響）
docker compose pull && docker compose up -d --build

# 備份使用者資料
docker run --rm -v stock_user_data:/src -v $(pwd):/dst alpine \
  tar czf /dst/backup_users_$(date +%F).tar.gz -C /src .
```

### 架構保證

- **Repository Pattern** 介面不變：未來替換 SQLite / PostgreSQL 不影響業務邏輯
- `user_id` 已隔離，接入 Auth 系統時只需注入真實 user_id
- Streamlit Cloud / Hugging Face Space 部署時，需改用雲端 KV 儲存（接口不變，只換 Backend）

---

## Issue 2｜回測前瞻天數設計

### 概念說明

**前瞻天數（Forward Days）** = 訊號觸發後，持倉第 N 個**交易日**收盤的報酬。

> 例：Forward Days = 60 → 訊號日後第 60 個交易日（約 3 個月）的持有報酬

本系統使用的是**交易日**計算（非自然日），60 交易日 ≈ 3 個月，250 交易日 ≈ 1 年。

### 專業設置慣例

| 投資風格 | 交易日範圍 | 自然日約當 | 典型用途 |
|----------|----------|------------|----------|
| 短線 | 5–20 | 1–4 週 | 短期動能、事件驅動 |
| 中線 | 20–60 | 1–3 個月 | 財報週期、趨勢跟隨 |
| 波段 | 60–120 | 3–6 個月 | 產業輪動、半年績效評估 |
| 長線 | 120–250 | 6–12 個月 | 年度績效、策略穩定性驗證 |
| 超長線 | 250–500 | 1–2 年 | 複利效果評估、長線價值投資 |

### 改進

- 原：`selectbox([20, 40, 60, 120])` — 4 個固定選項
- 改：`slider(5~500, step=5)` — 連續調整，含說明文字
- 預設值 60（中線，最常用觀察節點）

### 是否需要更長時間？

**視策略性質而定**。Strategy D 是基於 KD + MACD 的中短線動能策略，**60–120 交易日**是最合理的評估窗口。若延伸至 250 日可評估策略的長線穩定性，但訊號次數少時統計意義下降。建議：

- 主要參考：60 日（3 個月）
- 輔助驗證：120 日（6 個月）
- 壓力測試：250 日（1 年）

---

## Issue 3｜各訊號前瞻報酬直條圖 — 去除日期空白

### 問題

X 軸使用**日曆日期**，兩個買點之間若無訊號，圖表中間出現大量空白。此設計意義有限，因為每根直條代表**獨立的交易事件**，並非連續時間序列。

### 改進

- X 軸改為**序列索引**（`#1`, `#2`, `#3`…）
- Hover 顯示完整資訊（進場日、前瞻日、報酬率）
- 使用 `type="category"` 確保等間距排列，無空隙

### 視覺意義

此圖的核心價值是**每次交易的個別報酬分佈**，適合觀察：
- 勝率分佈（紅綠比例）
- 最大虧損 / 最大獲利
- 是否有連續虧損序列

---

## Issue 4｜累積報酬曲線 — 等間距序列

### 問題

若使用日期為 X 軸，無訊號的日期不代表任何交易，曲線只是「在無意義的日子重複最後一個值」，視覺上混亂。

### 改進

- X 軸改為訊號序列（與 Issue 3 一致）
- 曲線代表「每次交易後的累積資金曲線」
- 可清晰看出策略的**最大回撤區間**與**複利效果**

### 計算方式

```
equity[n] = ∏(1 + r[i]/100) for i in 1..n  — 1
```
每個訊號的報酬複利累積，反映實際資金曲線（假設全倉、無手續費）。

---

## Issue 5｜Strategy D 訊號標示改進

### 問題

原色 `GOLD = #C8A86A`（淺金黃色），在 Morandi 低飽和度背景下辨識度不足，尤其與蠟燭圖的暖色調接近。

### 改進

| 模式 | 原色 | 新色 | 說明 |
|------|------|------|------|
| 亮色（Light） | `#C8A86A` 淺金黃 | `#D4440C` 珊瑚橙紅 | 高飽和度，與背景高對比 |
| 暗色（Dark） | `#F0C060` 亮金黃 | `#FF6B35` 亮橙色 | 深色背景下更醒目 |

同步調整：
- 箭頭字體放大：`size 13 → 16`
- 垂直虛線加粗：`width 1 → 1.5`
- 透明度提升：`opacity 0.35 → 0.6`
- 三角形標記放大：`size 12 → 15`，加白色描邊

---

## Issue 6｜Dashboard K 線圖假日空格

### 問題

Plotly 預設以**日曆時間**為 X 軸，週六日及市場休市日（例如元旦、春節）會顯示空白間隔，導致技術指標看起來「斷開」。

### 改進

使用 Plotly `rangebreaks` 功能自動跳過非交易日：

```python
rangebreaks = [
    dict(bounds=["sat", "mon"]),  # 跳過週六、週日
    dict(values=holiday_dates),   # 跳過市場假日
]
```

假日偵測邏輯：以資料中**實際存在的交易日**為基準，比對該時間範圍內所有工作日，差集即為市場假日。

### 資料錯誤處理

**當天無股價不一定是休市**，可能的原因：
1. 休市（節假日、停牌）→ 正常，應跳過
2. yfinance API 失敗 → 資料缺失，可能造成指標誤算
3. 停牌超過 1 天 → 應保留最後已知價格或標記

目前處理策略：
- 短暫缺失（1–3 天）→ `rangebreaks` 跳過，指標計算已用 `ffill` 補漏
- 長期停牌 → 目前無特殊處理（初期不實作）
- API 錯誤 → `fetch_prices_for_strategy` 已有 try/except，回傳 empty DataFrame

---

## Issue 7｜掃描器結果頁面體驗

### 問題

`st.dataframe()` 預設高度約 200px，掃描 20 支股票時結果被截斷，需要上下滾動，且頁面下方大量空白浪費。

### 改進

動態計算表格高度：

```python
table_height = max(300, min(36 * len(show_df) + 38, 900))
```

- 每列 36px（含邊距）+ 38px 表頭
- 最小 300px，最大 900px（避免超出視窗）

---

## Issue 8｜預設自選清單更新

新增 20 支股票作為系統預設清單，涵蓋：

| 類別 | 股票 |
|------|------|
| 美國 ETF | GLD, SOXX, VOO, ITA |
| 美股個股 | MU, NVDA, PLTR, TSLA, META, MSFT, GOOGL |
| 台股個股 | 2330.TW, 2317.TW, 3037.TW, 2382.TW, 6757.TW |
| 台股 ETF | 0050.TW, 00922.TW, 00981A.TW, 00980A.TW |

> 注意：`00981A.TW` / `00980A.TW` 為槓桿/反向 ETF，yfinance 可能支援度有限，如取不到資料將顯示錯誤提示，不影響其他股票。

---

## 可擴展性考量

| 面向 | 現況 | 未來擴充路徑 |
|------|------|------------|
| 儲存層 | JSON + Pickle（本地） | 換 SQLite → PostgreSQL，只改 Backend，接口不變 |
| 多用戶 | `user_id="local"` | 接入 Auth → 注入真實 user_id，Repository 層零修改 |
| 新策略 | Strategy Pattern | 新增 `src/strategies/strategy_e.py`，Register 即可 |
| 前瞻分析 | 單一前瞻天數 | 可擴充為多天數批量回測（Heat Map 顯示） |
| 假日處理 | yfinance 自動跳過 | 未來可接入 trading_calendars 套件精確管理各市場休市日 |
| Docker | 單容器 | 可拆分 Streamlit + Redis 快取 + 排程資料更新服務 |
