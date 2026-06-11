import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { usePoll } from "./usePoll";
import { KlineChart } from "./components/KlineChart";
import { MarketBar } from "./components/MarketBar";
import { ScannerTable } from "./components/ScannerTable";
import { SidePanel } from "./components/SidePanel";
import { SymbolHeader } from "./components/SymbolHeader";
import { Watchlist } from "./components/Watchlist";
import type { KlineResponse, Quote, WatchlistItem } from "./types";

const UPDOWN_COLORS = {
  tw: { up: "#f23645", down: "#089981" },
  us: { up: "#089981", down: "#f23645" },
} as const;

export default function App() {
  const [updown, setUpdown] = useState<"tw" | "us">(
    () => (localStorage.getItem("updown") as "tw" | "us") || "tw",
  );
  useEffect(() => {
    document.documentElement.dataset.updown = updown;
    localStorage.setItem("updown", updown);
  }, [updown]);

  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("theme") as "dark" | "light") || "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const [scannerH, setScannerH] = useState(
    () => Number(localStorage.getItem("scanner-h")) || 230,
  );
  useEffect(() => localStorage.setItem("scanner-h", String(scannerH)), [scannerH]);

  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [interval, setInterval_] = useState("1d");
  const [period, setPeriod] = useState("1Y");
  const [strategyId, setStrategyId] = useState("strategy_d");
  const [kline, setKline] = useState<KlineResponse | null>(null);
  const [klineError, setKlineError] = useState<string | null>(null);
  const [alertMode, setAlertMode] = useState(false);
  const [pendingPrice, setPendingPrice] = useState<number | null>(null);

  const { data: strategies } = usePoll(() => api.strategies(), 3_600_000);

  const loadWatchlist = useCallback(async () => {
    const list = await api.watchlist();
    setItems(list);
    setSymbol((current) => current || list[0]?.ticker || "2330.TW");
  }, []);

  useEffect(() => {
    loadWatchlist().catch(() => {});
  }, [loadWatchlist]);

  const symbols = useMemo(() => {
    const set = new Set(items.map((i) => i.ticker));
    if (symbol) set.add(symbol);
    return [...set];
  }, [items, symbol]);

  const { data: quoteList } = usePoll(
    () => (symbols.length ? api.quotes(symbols) : Promise.resolve([] as Quote[])),
    8_000,
    [symbols.join(",")],
  );
  const quotes = useMemo(
    () => Object.fromEntries((quoteList ?? []).map((q) => [q.symbol, q])),
    [quoteList],
  );

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setKlineError(null);
    api
      .kline(symbol, interval, period, strategyId)
      .then((data) => !cancelled && setKline(data))
      .catch((err: Error) => !cancelled && setKlineError(err.message));
    return () => {
      cancelled = true;
    };
  }, [symbol, interval, period, strategyId]);

  const { data: allAlerts, refresh: refreshAlerts } = usePoll(() => api.alerts(), 30_000);
  const symbolAlerts = useMemo(
    () => (allAlerts ?? []).filter((a) => a.ticker === symbol),
    [allAlerts, symbol],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAlertMode(false);
        setPendingPrice(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const { up: upColor, down: downColor } = UPDOWN_COLORS[updown];

  return (
    <div className="app" style={{ gridTemplateRows: `42px 1fr ${scannerH}px` }}>
      <MarketBar
        updown={updown}
        onToggleUpdown={() => setUpdown(updown === "tw" ? "us" : "tw")}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      />
      <Watchlist
        items={items}
        quotes={quotes}
        selected={symbol}
        onSelect={setSymbol}
        onAdd={async (ticker) => {
          await api.addWatchlist(ticker);
          await loadWatchlist();
        }}
        onRemove={async (ticker) => {
          await api.removeWatchlist(ticker);
          await loadWatchlist();
        }}
      />
      <main className="main">
        <SymbolHeader
          symbol={symbol}
          quote={quotes[symbol]}
          interval={interval}
          setInterval={setInterval_}
          period={period}
          setPeriod={setPeriod}
          strategyId={strategyId}
          setStrategyId={setStrategyId}
          strategies={strategies ?? []}
        />
        {klineError && <div className="error-banner">{klineError}</div>}
        <KlineChart
          data={kline}
          alerts={symbolAlerts}
          upColor={upColor}
          downColor={downColor}
          theme={theme}
          alertMode={alertMode}
          onAlertPrice={(price) => {
            setPendingPrice(price);
            setAlertMode(false);
          }}
        />
      </main>
      <SidePanel
        symbol={symbol}
        quote={quotes[symbol]}
        alerts={allAlerts ?? []}
        refreshAlerts={refreshAlerts}
        alertMode={alertMode}
        setAlertMode={setAlertMode}
        pendingPrice={pendingPrice}
        clearPendingPrice={() => setPendingPrice(null)}
      />
      <ScannerTable strategyId={strategyId} onSelect={setSymbol} onHeightChange={setScannerH} />
    </div>
  );
}
