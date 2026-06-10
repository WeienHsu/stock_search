import { useEffect, useRef, useState } from "react";
import type { Quote, WatchlistItem } from "../types";
import { fmtPct, fmtPrice, trendClass } from "../format";

interface Props {
  items: WatchlistItem[];
  quotes: Record<string, Quote>;
  selected: string;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void>;
  onRemove: (ticker: string) => void;
}

function Row({
  item,
  quote,
  selected,
  onSelect,
  onRemove,
}: {
  item: WatchlistItem;
  quote?: Quote;
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
}) {
  const prevPrice = useRef<number | null>(null);
  const [flash, setFlash] = useState("");

  useEffect(() => {
    if (quote && prevPrice.current != null && quote.price !== prevPrice.current) {
      setFlash(quote.price > prevPrice.current ? "flash-up" : "flash-down");
      const id = setTimeout(() => setFlash(""), 850);
      prevPrice.current = quote.price;
      return () => clearTimeout(id);
    }
    if (quote) prevPrice.current = quote.price;
  }, [quote]);

  return (
    <div
      className={`wl-row ${selected ? "selected" : ""} ${flash}`}
      onClick={onSelect}
      onDoubleClick={onRemove}
      title="雙擊移除"
    >
      <span className="ticker">{item.ticker}</span>
      <span className={`price num ${trendClass(quote?.change_pct)}`}>
        {fmtPrice(quote?.price)}
      </span>
      <span className="name">{quote?.name || item.name}</span>
      <span className={`chg num ${trendClass(quote?.change_pct)}`}>
        {fmtPct(quote?.change_pct)}
      </span>
    </div>
  );
}

export function Watchlist({ items, quotes, selected, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const ticker = input.trim().toUpperCase();
    if (!ticker || busy) return;
    setBusy(true);
    try {
      await onAdd(ticker);
      setInput("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="watchlist">
      <div className="panel-title">自選清單</div>
      <div className="wl-add">
        <input
          placeholder="代號（2330 / AAPL）"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <button onClick={submit} disabled={busy}>
          ＋
        </button>
      </div>
      <div className="wl-rows">
        {items.map((item) => (
          <Row
            key={item.ticker}
            item={item}
            quote={quotes[item.ticker]}
            selected={item.ticker === selected}
            onSelect={() => onSelect(item.ticker)}
            onRemove={() => onRemove(item.ticker)}
          />
        ))}
        {items.length === 0 && <div className="empty-note">尚無自選股，輸入代號加入</div>}
      </div>
    </aside>
  );
}
