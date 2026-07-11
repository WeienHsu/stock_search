import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Alert, KlineResponse, SignalMode } from "./../types";
import { fmtPrice } from "../format";

const MA_COLORS: Record<string, string> = {
  "5": "#f0b90b",
  "10": "#3b82f6",
  "20": "#e879f9",
  "60": "#34d399",
};

const CHART_THEMES = {
  dark: { text: "#7d8696", grid: "rgba(125, 134, 150, 0.08)", separator: "#1f2633" },
  light: { text: "#5d6878", grid: "rgba(93, 104, 120, 0.14)", separator: "#d9dee7" },
} as const;

// Latest buy/sell markers use accent colors independent of the up/down palette:
// the up color is red in 紅漲綠跌 mode, which makes a red belowBar buy arrow blend
// into the red price line and volume bars. Blue/orange stay visible everywhere.
const LATEST_BUY = "#2979ff";
const LATEST_SELL = "#ff6d00";
// Early (divergence) markers: muted tints + circle shape so they read as
// tentative hints, clearly distinct from the solid confirmed arrows.
const EARLY_BUY = "#7eb6ff";
const EARLY_SELL = "#ffb27a";

// A buy at a deep negative bias (price far below MA20) is, per the bottom-strength
// study, a stronger bottom worth weighting more. Buys at/below this get emphasized.
const STRONG_BIAS = -8;
const BIAS_POS = "#34d399";
const BIAS_NEG = "#f97316";

const biasOf = (close: number, ma20: number | null | undefined): number | null =>
  ma20 == null || ma20 === 0 ? null : ((close - ma20) / ma20) * 100;

interface Props {
  data: KlineResponse | null;
  alerts: Alert[];
  upColor: string;
  downColor: string;
  theme: "dark" | "light";
  signalMode: SignalMode;
  showBias: boolean;
  alertMode: boolean;
  onAlertPrice: (price: number) => void;
}

interface Refs {
  chart: IChartApi;
  candles: ISeriesApi<"Candlestick">;
  volume: ISeriesApi<"Histogram">;
  ma: Record<string, ISeriesApi<"Line">>;
  macdHist: ISeriesApi<"Histogram">;
  macdLine: ISeriesApi<"Line">;
  macdSignal: ISeriesApi<"Line">;
  k: ISeriesApi<"Line">;
  d: ISeriesApi<"Line">;
  bias: ISeriesApi<"Histogram"> | null;
  markers: ISeriesMarkersPluginApi<Time>;
  priceLines: IPriceLine[];
}

function toTime(value: string): Time {
  if (value.includes(" ")) {
    return Math.floor(new Date(value.replace(" ", "T")).getTime() / 1000) as UTCTimestamp;
  }
  return value as Time;
}

export function KlineChart({ data, alerts, upColor, downColor, theme, signalMode, showBias, alertMode, onAlertPrice }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const refs = useRef<Refs | null>(null);
  const [legend, setLegend] = useState("");
  const alertModeRef = useRef(alertMode);
  alertModeRef.current = alertMode;
  const onAlertPriceRef = useRef(onAlertPrice);
  onAlertPriceRef.current = onAlertPrice;

  // Build chart once
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: CHART_THEMES.dark.text,
        fontSize: 11,
        panes: { separatorColor: CHART_THEMES.dark.separator },
      },
      grid: {
        vertLines: { color: CHART_THEMES.dark.grid },
        horzLines: { color: CHART_THEMES.dark.grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderVisible: false, rightOffset: 4 },
      rightPriceScale: { borderVisible: false },
    });

    const candles = chart.addSeries(CandlestickSeries, { borderVisible: false });
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    const ma: Record<string, ISeriesApi<"Line">> = {};
    for (const [period, color] of Object.entries(MA_COLORS)) {
      ma[period] = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
    }

    const macdHist = chart.addSeries(
      HistogramSeries,
      { lastValueVisible: false, priceLineVisible: false },
      1,
    );
    const macdLine = chart.addSeries(
      LineSeries,
      { color: "#3b82f6", lineWidth: 1, lastValueVisible: false, priceLineVisible: false },
      1,
    );
    const macdSignal = chart.addSeries(
      LineSeries,
      { color: "#f0b90b", lineWidth: 1, lastValueVisible: false, priceLineVisible: false },
      1,
    );

    const k = chart.addSeries(
      LineSeries,
      { color: "#3b82f6", lineWidth: 1, lastValueVisible: false, priceLineVisible: false },
      2,
    );
    const d = chart.addSeries(
      LineSeries,
      { color: "#f0b90b", lineWidth: 1, lastValueVisible: false, priceLineVisible: false },
      2,
    );

    const panes = chart.panes();
    panes[0]?.setStretchFactor(300);
    panes[1]?.setStretchFactor(70);
    panes[2]?.setStretchFactor(70);

    const markers = createSeriesMarkers(candles, []);

    chart.subscribeClick((param) => {
      if (!alertModeRef.current || !param.point) return;
      const price = candles.coordinateToPrice(param.point.y);
      if (price != null) onAlertPriceRef.current(Number(price));
    });

    refs.current = {
      chart,
      candles,
      volume,
      ma,
      macdHist,
      macdLine,
      macdSignal,
      k,
      d,
      bias: null,
      markers,
      priceLines: [],
    };
    return () => {
      chart.remove();
      refs.current = null;
    };
  }, []);

  // Follow app theme
  useEffect(() => {
    const r = refs.current;
    if (!r) return;
    const colors = CHART_THEMES[theme];
    r.chart.applyOptions({
      layout: { textColor: colors.text, panes: { separatorColor: colors.separator } },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
    });
  }, [theme]);

  // Push data + colors
  useEffect(() => {
    const r = refs.current;
    if (!r) return;
    r.candles.applyOptions({ upColor, downColor, wickUpColor: upColor, wickDownColor: downColor });
    if (!data) return;

    const candleData = data.candles.map((c) => ({
      time: toTime(c.time),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    r.candles.setData(candleData);

    r.volume.setData(
      data.candles.map((c) => ({
        time: toTime(c.time),
        value: c.volume ?? 0,
        color: c.close >= c.open ? `${upColor}55` : `${downColor}55`,
      })),
    );

    const line = (values: (number | null)[]) =>
      data.candles.flatMap((c, i) =>
        values[i] == null ? [] : [{ time: toTime(c.time), value: values[i] as number }],
      );

    for (const [period, series] of Object.entries(r.ma)) {
      series.setData(line(data.indicators.ma[period] ?? []));
    }
    r.macdLine.setData(line(data.indicators.macd.macd));
    r.macdSignal.setData(line(data.indicators.macd.signal));
    r.macdHist.setData(
      data.candles.flatMap((c, i) => {
        const v = data.indicators.macd.hist[i];
        return v == null
          ? []
          : [{ time: toTime(c.time), value: v, color: v >= 0 ? `${upColor}99` : `${downColor}99` }];
      }),
    );
    r.k.setData(line(data.indicators.kd.k));
    r.d.setData(line(data.indicators.kd.d));

    const byDate = new Map(data.candles.map((c) => [c.time.slice(0, 10), c]));
    const indexByDate = new Map(data.candles.map((c, i) => [c.time.slice(0, 10), i]));
    const ma20 = data.indicators.ma["20"] ?? [];
    const biasByDate = new Map(
      data.candles.map((c, i) => [c.time.slice(0, 10), biasOf(c.close, ma20[i])]),
    );
    const tierOf = (s: { tier?: string }) => s.tier ?? "confirmed";
    const all = data.signals
      .filter((s) => byDate.has(s.date) && s.type !== "neutral")
      .sort((a, b) => (a.date < b.date ? -1 : 1));

    // Confirmed arrows: collapse runs of the same signal on consecutive bars into
    // the latest one. lightweight-charts drops markers when adjacent-bar markers
    // cluster (even out-of-view clusters), which was hiding the most recent
    // buy/sell arrow once the chart was zoomed in.
    const visible = signalMode === "early" ? [] : all.filter((s) => tierOf(s) === "confirmed");
    const collapsed = visible.filter((s, i) => {
      const next = visible[i + 1];
      return !(
        next &&
        next.type === s.type &&
        (indexByDate.get(next.date) ?? 0) - (indexByDate.get(s.date) ?? 0) <= 1
      );
    });
    const lastBuy = collapsed.filter((s) => s.type === "buy").map((s) => s.date).sort().at(-1);
    const lastSell = collapsed.filter((s) => s.type === "sell").map((s) => s.date).sort().at(-1);
    // Latest signal of each type is emphasized; history stays small and quiet.
    // Buy arrows also encode bias-below-MA20 strength: a deep negative bias (a
    // stronger bottom) is enlarged and labelled with the bias %; the latest buy
    // additionally carries 「買」. Sell arrows are unchanged (bias unvalidated there).
    const confirmedMarkers: SeriesMarker<Time>[] = collapsed.map((s) => {
      const isLatest = s.date === (s.type === "buy" ? lastBuy : lastSell);
      const bias = s.type === "buy" ? biasByDate.get(s.date) ?? null : null;
      const strong = bias != null && bias <= STRONG_BIAS;
      const biasStr = bias != null ? `${bias.toFixed(0)}%` : "";
      let text: string | undefined;
      if (s.type === "buy") {
        text = isLatest ? `買 ${biasStr}`.trim() : strong ? biasStr : undefined;
      } else {
        text = isLatest ? "賣" : undefined;
      }
      return {
        time: toTime(byDate.get(s.date)!.time),
        position: s.type === "buy" ? "belowBar" : "aboveBar",
        shape: s.type === "buy" ? "arrowUp" : "arrowDown",
        color: isLatest
          ? s.type === "buy"
            ? LATEST_BUY
            : LATEST_SELL
          : s.type === "buy"
            ? upColor
            : downColor,
        text,
        size: isLatest || strong ? 2 : 1,
      };
    });

    // Early (divergence) hints: muted circles labelled「早」, on the same side as
    // the eventual arrow so they read as a precursor to it.
    const earlySigs = signalMode === "confirmed" ? [] : all.filter((s) => tierOf(s) === "early");
    const earlyMarkers: SeriesMarker<Time>[] = earlySigs.map((s) => ({
      time: toTime(byDate.get(s.date)!.time),
      position: s.type === "buy" ? "belowBar" : "aboveBar",
      shape: "circle",
      color: s.type === "buy" ? EARLY_BUY : EARLY_SELL,
      text: "早",
      size: 1,
    }));

    // Daily markers carry ISO date strings (chronological under string compare);
    // intraday markers carry numeric timestamps. Handle both.
    const markerList = [...confirmedMarkers, ...earlyMarkers].sort((a, b) => {
      if (typeof a.time === "number" && typeof b.time === "number") return a.time - b.time;
      return String(a.time) < String(b.time) ? -1 : String(a.time) > String(b.time) ? 1 : 0;
    });
    r.markers.setMarkers(markerList);
    r.chart.timeScale().fitContent();
  }, [data, upColor, downColor, signalMode]);

  // Optional bias (distance below MA20) sub-pane, created on demand (default off)
  // so it doesn't crowd the chart. Removing the series drops its (now empty) pane.
  useEffect(() => {
    const r = refs.current;
    if (!r) return;
    if (!showBias) {
      if (r.bias) {
        r.chart.removeSeries(r.bias);
        r.bias = null;
      }
      return;
    }
    if (!r.bias) {
      r.bias = r.chart.addSeries(
        HistogramSeries,
        { priceFormat: { type: "price", precision: 1, minMove: 0.1 }, lastValueVisible: false, priceLineVisible: false },
        3,
      );
      r.bias.createPriceLine({
        price: STRONG_BIAS,
        color: BIAS_NEG,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "強底",
      });
      const panes = r.chart.panes();
      panes[0]?.setStretchFactor(300);
      panes[1]?.setStretchFactor(70);
      panes[2]?.setStretchFactor(70);
      panes[3]?.setStretchFactor(70);
    }
    if (data) {
      const ma20 = data.indicators.ma["20"] ?? [];
      r.bias.setData(
        data.candles.flatMap((c, i) => {
          const b = biasOf(c.close, ma20[i]);
          return b == null ? [] : [{ time: toTime(c.time), value: b, color: b < 0 ? BIAS_NEG : BIAS_POS }];
        }),
      );
    }
  }, [data, showBias]);

  // Alert price lines
  useEffect(() => {
    const r = refs.current;
    if (!r) return;
    for (const lineRef of r.priceLines) r.candles.removePriceLine(lineRef);
    r.priceLines = alerts
      .filter((a) => a.enabled && !a.triggered_at)
      .map((a) =>
        r.candles.createPriceLine({
          price: a.threshold,
          color: a.direction === "above" ? upColor : downColor,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: a.direction === "above" ? "▲警示" : "▼警示",
        }),
      );
  }, [alerts, data, upColor, downColor]);

  // Crosshair legend
  useEffect(() => {
    const r = refs.current;
    if (!r || !data) return;
    const handler = (param: { time?: Time }) => {
      if (!param.time) {
        setLegend("");
        return;
      }
      const target = typeof param.time === "string" ? param.time : null;
      const idx = data.candles.findIndex((c) =>
        target ? c.time === target : toTime(c.time) === param.time,
      );
      const candle = idx >= 0 ? data.candles[idx] : undefined;
      if (!candle) {
        setLegend("");
        return;
      }
      const bias = biasOf(candle.close, (data.indicators.ma["20"] ?? [])[idx]);
      const biasStr = bias != null ? `  乖離 ${bias.toFixed(1)}%` : "";
      setLegend(
        `O ${fmtPrice(candle.open)}  H ${fmtPrice(candle.high)}  L ${fmtPrice(candle.low)}  C ${fmtPrice(candle.close)}${biasStr}`,
      );
    };
    r.chart.subscribeCrosshairMove(handler);
    return () => r.chart.unsubscribeCrosshairMove(handler);
  }, [data]);

  const signalDates = (type: "buy" | "sell") =>
    (data?.signals ?? [])
      .filter((s) => s.type === type && (s.tier ?? "confirmed") === "confirmed")
      .map((s) => s.date)
      .sort()
      .at(-1);
  const lastBuyDate = signalDates("buy");
  const lastSellDate = signalDates("sell");

  return (
    <div className="chart-host">
      <div className="chart-hint">
        {alertMode ? "點擊圖表價位以建立到價警示（Esc 取消）" : legend}
      </div>
      {(lastBuyDate || lastSellDate) && (
        <div className="chart-badges">
          {lastBuyDate && (
            <span style={{ color: LATEST_BUY }}>▲ 最近買進 {lastBuyDate.slice(5)}</span>
          )}
          {lastSellDate && (
            <span style={{ color: LATEST_SELL }}>▼ 最近賣出 {lastSellDate.slice(5)}</span>
          )}
        </div>
      )}
      <div ref={containerRef} className="lw-container" style={alertMode ? { cursor: "crosshair" } : undefined} />
    </div>
  );
}
