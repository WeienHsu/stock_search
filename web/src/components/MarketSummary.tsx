import { api } from "../api";
import { usePoll } from "../usePoll";
import { fmtLots, fmtPct, fmtPrice, fmtVolume, trendClass } from "../format";

const INDEX_LABELS: Record<string, string> = {
  taiex: "加權指數",
  sp500: "S&P 500",
  nasdaq: "NASDAQ",
  usdtwd: "USD/TWD",
};

export function MarketSummary() {
  const { data } = usePoll(() => api.market(), 300_000);

  if (!data) return <div className="empty-note">大盤資料載入中…</div>;

  const inst = (data.institutional ?? []).slice(-10).reverse();
  const fg = data.fear_greed;
  const breadth = data.breadth;

  return (
    <>
      <div className="stat-grid">
        {Object.entries(INDEX_LABELS).map(([key, label]) => {
          const snap = data.indices?.[key];
          if (!snap?.close) return null;
          return (
            <div className="stat-card" key={key}>
              <div className="label">
                {label}
                {snap.ma_score != null ? `（多頭 ${snap.ma_score}/4）` : ""}
              </div>
              <div className={`value num ${trendClass(snap.change_pct)}`}>
                {fmtPrice(snap.close)} {fmtPct(snap.change_pct)}
              </div>
            </div>
          );
        })}
        {fg?.score != null && (
          <div className="stat-card">
            <div className="label">CNN Fear &amp; Greed</div>
            <div className={`value num ${fg.score < 40 ? "down" : fg.score > 60 ? "up" : "flat"}`}>
              {Math.round(fg.score)}（{fg.rating}）
            </div>
          </div>
        )}
        {breadth?.ratio != null && (
          <div className="stat-card">
            <div className="label">台股委買賣比</div>
            <div className={`value num ${trendClass((breadth.ratio ?? 1) - 1)}`}>
              {Number(breadth.ratio).toFixed(2)}
            </div>
          </div>
        )}
        {data.margin?.margin_balance != null && (
          <div className="stat-card">
            <div className="label">全市場融資餘額</div>
            <div className="value num">{fmtVolume(data.margin.margin_balance)}</div>
          </div>
        )}
        {data.valuation?.median_pe != null && (
          <div className="stat-card">
            <div className="label">台股本益比中位數</div>
            <div className="value num">{data.valuation.median_pe.toFixed(1)}</div>
          </div>
        )}
      </div>

      {inst.length > 0 && (
        <>
          <div className="panel-title" style={{ border: "none", padding: "4px 0" }}>
            台股法人買賣超（張）
          </div>
          <table className="mini-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>外資</th>
                <th>投信</th>
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
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
