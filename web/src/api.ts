import type {
  Alert,
  AlertEvent,
  InboxMessage,
  KlineResponse,
  MarketOverview,
  Quote,
  ScanRow,
  StrategyInfo,
  WatchlistItem,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail ?? `${resp.status} ${resp.statusText}`);
  }
  return resp.json();
}

export const api = {
  quotes: (symbols: string[]) =>
    request<Quote[]>(`/api/quotes?symbols=${encodeURIComponent(symbols.join(","))}`),
  kline: (symbol: string, interval: string, period: string, strategyId: string) =>
    request<KlineResponse>(
      `/api/kline/${encodeURIComponent(symbol)}?interval=${interval}&period=${period}&strategy_id=${strategyId}`,
    ),
  strategies: () => request<StrategyInfo[]>("/api/strategies"),
  watchlist: () => request<WatchlistItem[]>("/api/watchlist"),
  addWatchlist: (ticker: string, name = "") =>
    request<WatchlistItem>("/api/watchlist", {
      method: "POST",
      body: JSON.stringify({ ticker, name }),
    }),
  removeWatchlist: (ticker: string) =>
    request<{ ok: boolean }>(`/api/watchlist/${encodeURIComponent(ticker)}`, {
      method: "DELETE",
    }),
  alerts: () => request<Alert[]>("/api/alerts"),
  createAlert: (ticker: string, direction: "above" | "below", threshold: number) =>
    request<Alert>("/api/alerts", {
      method: "POST",
      body: JSON.stringify({ ticker, direction, threshold }),
    }),
  setAlertEnabled: (id: string, enabled: boolean) =>
    request<{ ok: boolean }>(`/api/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  deleteAlert: (id: string) =>
    request<{ ok: boolean }>(`/api/alerts/${id}`, { method: "DELETE" }),
  alertEvents: (limit = 30) => request<AlertEvent[]>(`/api/alerts/events?limit=${limit}`),
  scan: (strategyId: string) => request<ScanRow[]>(`/api/scan?strategy_id=${strategyId}`),
  market: () => request<MarketOverview>("/api/market"),
  inbox: () => request<{ messages: InboxMessage[]; unread: number }>("/api/inbox"),
  markRead: (id: string) =>
    request<{ ok: boolean }>(`/api/inbox/${id}/read`, { method: "POST" }),
};
