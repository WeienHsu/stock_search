import { fmtChange, fmtPct, fmtPrice, fmtVolume, trendClass } from "../format";
import type { Quote, SignalMode, StrategyInfo } from "../types";

const INTERVALS = ["1d", "60m", "15m", "5m"] as const;
const PERIODS = ["1M", "3M", "6M", "1Y", "3Y", "5Y"] as const;
const SIGNAL_MODES: { value: SignalMode; label: string }[] = [
  { value: "confirmed", label: "原始" },
  { value: "early", label: "早期" },
  { value: "both", label: "兩者" },
];

interface Props {
  symbol: string;
  quote?: Quote;
  interval: string;
  setInterval: (v: string) => void;
  period: string;
  setPeriod: (v: string) => void;
  strategyId: string;
  setStrategyId: (v: string) => void;
  strategies: StrategyInfo[];
  signalMode: SignalMode;
  setSignalMode: (v: SignalMode) => void;
  showBias: boolean;
  setShowBias: (v: boolean) => void;
}

export function SymbolHeader({
  symbol,
  quote,
  interval,
  setInterval,
  period,
  setPeriod,
  strategyId,
  setStrategyId,
  strategies,
  signalMode,
  setSignalMode,
  showBias,
  setShowBias,
}: Props) {
  const cls = trendClass(quote?.change_pct);
  return (
    <div className="symbol-header">
      <span className="sym">{symbol || "—"}</span>
      {quote?.name && <span className="sym-name">{quote.name}</span>}
      <span className={`big-price num ${cls}`}>{fmtPrice(quote?.price)}</span>
      <span className={`num ${cls}`}>
        {fmtChange(quote?.change)} ({fmtPct(quote?.change_pct)})
      </span>
      <div className="ohlc num">
        <span>開 {fmtPrice(quote?.open)}</span>
        <span>高 {fmtPrice(quote?.high)}</span>
        <span>低 {fmtPrice(quote?.low)}</span>
        <span>量 {fmtVolume(quote?.volume)}</span>
      </div>
      <div className="controls">
        {INTERVALS.map((v) => (
          <button key={v} className={interval === v ? "active" : ""} onClick={() => setInterval(v)}>
            {v === "1d" ? "日K" : v}
          </button>
        ))}
        <select value={period} onChange={(e) => setPeriod(e.target.value)}>
          {PERIODS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select value={strategyId} onChange={(e) => setStrategyId(e.target.value)} title="訊號策略">
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id}
            </option>
          ))}
        </select>
        <span className="signal-mode" title="買賣箭頭：原始(確認) / 早期(背離) / 兩者並陳">
          {SIGNAL_MODES.map((m) => (
            <button
              key={m.value}
              className={signalMode === m.value ? "active" : ""}
              onClick={() => setSignalMode(m.value)}
            >
              {m.label}
            </button>
          ))}
        </span>
        <button
          className={showBias ? "active" : ""}
          onClick={() => setShowBias(!showBias)}
          title="顯示/隱藏 乖離率(離 MA20) 副圖；買訊深負乖離 = 較強的底"
        >
          乖離
        </button>
      </div>
    </div>
  );
}
