import { useMemo, useRef, useState } from "react";
import { api } from "../api";
import { fmtPct, fmtPrice, trendClass } from "../format";
import type { ScanRow } from "../types";

interface Props {
  strategyId: string;
  onSelect: (ticker: string) => void;
  onHeightChange: (height: number) => void;
}

type SortKey = "close" | "chg" | "buy" | "sell" | "score";

interface SortState {
  key: SortKey;
  dir: 1 | -1;
}

/** Rank a signal column: triggered > recent > none/error. */
function signalRank(active: boolean, status: string): number {
  if (active) return 2;
  if (status.includes("近期")) return 1;
  return 0;
}

function sortValue(row: ScanRow, key: SortKey): number | string {
  switch (key) {
    case "close":
      return row.current_close ?? 0;
    case "chg":
      return row.daily_change_pct ?? -Infinity;
    case "buy":
      return signalRank(row.buy_signal, row.buy_status) * 1e10 + dateScore(row.last_buy_date);
    case "sell":
      return signalRank(row.sell_signal, row.sell_status) * 1e10 + dateScore(row.last_sell_date);
    case "score":
      return row.ma_bullish_score ?? 0;
  }
}

function dateScore(date: string): number {
  const ts = Date.parse(date);
  return Number.isNaN(ts) ? 0 : ts / 1e6;
}

export function ScannerTable({ strategyId, onSelect, onHeightChange }: Props) {
  const [rows, setRows] = useState<ScanRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortState | null>({ key: "buy", dir: -1 });
  const sectionRef = useRef<HTMLElement>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setRows(await api.scan(strategyId));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggleSort = (key: SortKey) => {
    setSort((prev) =>
      prev?.key === key ? (prev.dir === -1 ? { key, dir: 1 } : null) : { key, dir: -1 },
    );
  };

  const sorted = useMemo(() => {
    if (!rows) return null;
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const va = sortValue(a, sort.key);
      const vb = sortValue(b, sort.key);
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir;
    });
  }, [rows, sort]);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startH = sectionRef.current?.offsetHeight ?? 230;
    const move = (ev: MouseEvent) => {
      const next = Math.min(Math.max(startH + (startY - ev.clientY), 110), window.innerHeight * 0.65);
      onHeightChange(Math.round(next));
    };
    const up = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    document.body.style.cursor = "row-resize";
  };

  const arrow = (key: SortKey) => (sort?.key === key ? (sort.dir === -1 ? " ↓" : " ↑") : "");

  return (
    <section className="scanner" ref={sectionRef}>
      <div className="resize-handle" onMouseDown={startResize} title="拖拉調整高度" />
      <div className="panel-title">
        <span>策略掃描（{strategyId}）</span>
        <button onClick={run} disabled={busy}>
          {busy ? "掃描中…" : "執行掃描"}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="scanner-table-wrap">
        {sorted === null ? (
          <div className="empty-note">按「執行掃描」檢查自選清單的買賣訊號</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>代號</th>
                <th className="left">名稱</th>
                <th className="sortable" onClick={() => toggleSort("close")}>
                  收盤{arrow("close")}
                </th>
                <th className="sortable" onClick={() => toggleSort("chg")}>
                  漲跌%{arrow("chg")}
                </th>
                <th className="left sortable" onClick={() => toggleSort("buy")}>
                  買進訊號{arrow("buy")}
                </th>
                <th className="left sortable" onClick={() => toggleSort("sell")}>
                  賣出訊號{arrow("sell")}
                </th>
                <th className="left">趨勢</th>
                <th className="sortable" onClick={() => toggleSort("score")}>
                  多頭分數{arrow("score")}
                </th>
                <th className="left">支撐區</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.ticker} onClick={() => onSelect(row.ticker)}>
                  <td className="left num">{row.ticker}</td>
                  <td className="left">{row.name}</td>
                  <td className="num">{fmtPrice(row.current_close)}</td>
                  <td className={`num ${trendClass(row.daily_change_pct)}`}>
                    {fmtPct(row.daily_change_pct)}
                  </td>
                  <td className={`left ${row.buy_signal ? "sig-buy" : ""}`}>{row.buy_status}</td>
                  <td className={`left ${row.sell_signal ? "sig-sell" : ""}`}>{row.sell_status}</td>
                  <td className="left">{row.trend}</td>
                  <td className="num">{row.ma_bullish_score}/4</td>
                  <td className="left">{row.in_support_zone ? "✓" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
