import { useEffect, useState } from "react";
import { api } from "../api";
import { usePoll } from "../usePoll";
import { fmtPct, fmtPrice, trendClass } from "../format";
import type { IndexSnapshot } from "../types";

const LABELS: Record<string, string> = {
  taiex: "加權指數",
  sp500: "S&P 500",
  nasdaq: "NASDAQ",
  usdtwd: "USD/TWD",
};

function Item({ label, snap }: { label: string; snap?: IndexSnapshot }) {
  if (!snap?.close) return null;
  return (
    <div className="mb-item">
      <span className="label">{label}</span>
      <span className={`num ${trendClass(snap.change_pct)}`}>
        {fmtPrice(snap.close)} {fmtPct(snap.change_pct)}
      </span>
    </div>
  );
}

export function MarketBar({
  updown,
  onToggleUpdown,
}: {
  updown: "tw" | "us";
  onToggleUpdown: () => void;
}) {
  const { data } = usePoll(() => api.market(), 120_000);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const fg = data?.fear_greed;
  const breadth = data?.breadth;

  return (
    <header className="marketbar">
      <span className="brand">📈 Stock Intelligence</span>
      {Object.entries(LABELS).map(([key, label]) => (
        <Item key={key} label={label} snap={data?.indices?.[key]} />
      ))}
      {fg?.score != null && (
        <div className="mb-item">
          <span className="label">Fear &amp; Greed</span>
          <span className={`num ${fg.score < 40 ? "down" : fg.score > 60 ? "up" : "flat"}`}>
            {Math.round(fg.score)} {fg.rating}
          </span>
        </div>
      )}
      {breadth?.ratio != null && (
        <div className="mb-item">
          <span className="label">委買賣比</span>
          <span className={`num ${trendClass((breadth.ratio ?? 1) - 1)}`}>
            {Number(breadth.ratio).toFixed(2)}
          </span>
        </div>
      )}
      <div className="spacer" />
      <button className="ghost" onClick={onToggleUpdown} title="切換紅漲綠跌 / 綠漲紅跌">
        {updown === "tw" ? "紅漲綠跌" : "綠漲紅跌"}
      </button>
      <span className="clock num">
        {now.toLocaleTimeString("zh-TW", { hour12: false })}
      </span>
    </header>
  );
}
