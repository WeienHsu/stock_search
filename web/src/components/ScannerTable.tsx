import { useState } from "react";
import { api } from "../api";
import { fmtPct, fmtPrice, trendClass } from "../format";
import type { ScanRow } from "../types";

interface Props {
  strategyId: string;
  onSelect: (ticker: string) => void;
}

export function ScannerTable({ strategyId, onSelect }: Props) {
  const [rows, setRows] = useState<ScanRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <section className="scanner">
      <div className="panel-title">
        <span>策略掃描（{strategyId}）</span>
        <button onClick={run} disabled={busy}>
          {busy ? "掃描中…" : "執行掃描"}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="scanner-table-wrap">
        {rows === null ? (
          <div className="empty-note">按「執行掃描」檢查自選清單的買賣訊號</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>代號</th>
                <th className="left">名稱</th>
                <th>收盤</th>
                <th>漲跌%</th>
                <th className="left">買進訊號</th>
                <th className="left">賣出訊號</th>
                <th className="left">趨勢</th>
                <th>多頭分數</th>
                <th className="left">支撐區</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
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
