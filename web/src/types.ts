export interface Quote {
  symbol: string;
  name: string;
  price: number;
  prev_close: number | null;
  change: number;
  change_pct: number;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  market: "TW" | "US";
  ts: number;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface KlineResponse {
  symbol: string;
  interval: string;
  candles: Candle[];
  indicators: {
    ma: Record<string, (number | null)[]>;
    kd: { k: (number | null)[]; d: (number | null)[] };
    macd: {
      macd: (number | null)[];
      signal: (number | null)[];
      hist: (number | null)[];
    };
  };
  signals: { date: string; type: "buy" | "sell" | "neutral"; strength: number }[];
}

export interface WatchlistItem {
  ticker: string;
  name: string;
}

export interface Alert {
  id: string;
  ticker: string;
  type: string;
  direction: "above" | "below";
  threshold: number;
  enabled: boolean;
  triggered_at: number | null;
  expires_at: number | null;
  created_at: number;
}

export interface AlertEvent {
  id: string;
  alert_id: string;
  ticker: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: number;
}

export interface ScanRow {
  ticker: string;
  name: string;
  buy_signal: boolean;
  sell_signal: boolean;
  buy_status: string;
  sell_status: string;
  last_buy_date: string;
  last_sell_date: string;
  current_close: number;
  daily_change_pct: number | null;
  ma_bullish_score: number;
  trend: string;
  in_support_zone: boolean;
}

export interface IndexSnapshot {
  date?: string;
  close?: number;
  change_pct?: number;
  kd_status?: string;
  macd_status?: string;
  ma_score?: number;
}

export interface MarketOverview {
  indices: Record<string, IndexSnapshot>;
  breadth: {
    available?: boolean;
    buy_sell_diff?: number;
    ratio?: number;
  } | null;
  fear_greed: { score?: number; rating?: string } | null;
  institutional: {
    date: string;
    foreign_net_lots: number | null;
    investment_trust_net_lots: number | null;
  }[];
  margin: { margin_balance?: number; short_balance?: number } | null;
  valuation: { median_pe?: number; average_pe?: number; date?: string } | null;
}

export interface ChipResponse {
  supported: boolean;
  ticker: string;
  qfiis_pct?: number | null;
  summary?: {
    foreign_5d_lots?: number;
    investment_trust_5d_lots?: number;
    dealer_5d_lots?: number;
    margin_change_lots?: number;
    margin_change_pct?: number;
    margin_trend?: string;
  };
  institutional?: {
    date: string;
    foreign_net_lots: number | null;
    investment_trust_net_lots: number | null;
    dealer_net_lots: number | null;
  }[];
  margin?: {
    date: string;
    margin_balance: number | null;
    short_balance: number | null;
  }[];
}

export interface InboxMessage {
  id: string;
  subject: string;
  body: string;
  severity: string;
  read_at: number | null;
  created_at: number;
}

export interface StrategyInfo {
  id: string;
  default_params: Record<string, unknown>;
}
