import { useEffect, useState } from "react";
import { api } from "../api";
import { fmtLots, fmtPrice, trendClass } from "../format";
import type { ChipResponse } from "../types";

export function ChipPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<ChipResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setLoading(true);
    api
      .chip(symbol)
      .then((resp) => !cancelled && setData(resp))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (loading && data?.ticker !== symbol) return <div className="empty-note">籌碼載入中…</div>;
  if (!data) return <div className="empty-note">無籌碼資料</div>;
  if (!data.supported) return <div className="empty-note">籌碼資料僅支援台股</div>;

  const s = data.summary ?? {};
  const inst = (data.institutional ?? []).slice(-10).reverse();
  const lastMargin = (data.margin ?? []).slice(-1)[0];

  return (
    <>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="label">外資 近5日</div>
          <div className={`value num ${trendClass(s.foreign_5d_lots)}`}>
            {fmtLots(s.foreign_5d_lots)} 張
          </div>
        </div>
        <div className="stat-card">
          <div className="label">投信 近5日</div>
          <div className={`value num ${trendClass(s.investment_trust_5d_lots)}`}>
            {fmtLots(s.investment_trust_5d_lots)} 張
          </div>
        </div>
        <div className="stat-card">
          <div className="label">自營商 近5日</div>
          <div className={`value num ${trendClass(s.dealer_5d_lots)}`}>
            {fmtLots(s.dealer_5d_lots)} 張
          </div>
        </div>
        <div className="stat-card">
          <div className="label">外資持股</div>
          <div className="value num">
            {data.qfiis_pct != null ? `${data.qfiis_pct.toFixed(2)}%` : "—"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">融資餘額（張）</div>
          <div className="value num">{fmtPrice(lastMargin?.margin_balance)}</div>
        </div>
        <div className="stat-card">
          <div className="label">融資 20日趨勢</div>
          <div className={`value num ${trendClass(s.margin_change_lots)}`}>
            {s.margin_trend ?? "—"} {s.margin_change_pct != null ? `${s.margin_change_pct}%` : ""}
          </div>
        </div>
      </div>

      <div className="panel-title" style={{ border: "none", padding: "4px 0" }}>
        三大法人買賣超（張）
      </div>
      <table className="mini-table">
        <thead>
          <tr>
            <th>日期</th>
            <th>外資</th>
            <th>投信</th>
            <th>自營</th>
          </tr>
        </thead>
        <tbody>
          {inst.map((row) => (
            <tr key={row.date}>
              <td className="num">{row.date.slice(5)}</td>
              <td className={`num ${trendClass(row.foreign_net_lots)}`}>
                {fmtLots(row.foreign_net_lots)}
              </td>
              <td className={`num ${trendClass(row.investment_trust_net_lots)}`}>
                {fmtLots(row.investment_trust_net_lots)}
              </td>
              <td className={`num ${trendClass(row.dealer_net_lots)}`}>
                {fmtLots(row.dealer_net_lots)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
