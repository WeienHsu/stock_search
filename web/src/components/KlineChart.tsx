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
import type { Alert, KlineResponse } from "./../types";
import { fmtPrice } from "../format";

const MA_COLORS: Record<string, string> = {
  "5": "#f0b90b",
  "10": "#3b82f6",
  "20": "#e879f9",
  "60": "#34d399",
};

interface Props {
  data: KlineResponse | null;
  alerts: Alert[];
  upColor: string;
  downColor: string;
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
  markers: ISeriesMarkersPluginApi<Time>;
  priceLines: IPriceLine[];
}

function toTime(value: string): Time {
  if (value.includes(" ")) {
    return Math.floor(new Date(value.replace(" ", "T")).getTime() / 1000) as UTCTimestamp;
  }
  return value as Time;
}

export function KlineChart({ data, alerts, upColor, downColor, alertMode, onAlertPrice }: Props) {
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
    const style = getComputedStyle(document.documentElement);
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: style.getPropertyValue("--text-dim").trim() || "#7d8696",
        fontSize: 11,
        panes: { separatorColor: style.getPropertyValue("--border").trim() || "#1f2633" },
      },
      grid: {
        vertLines: { color: "rgba(125, 134, 150, 0.08)" },
        horzLines: { color: "rgba(125, 134, 150, 0.08)" },
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
      markers,
      priceLines: [],
    };
    return () => {
      chart.remove();
      refs.current = null;
    };
  }, []);

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
    const markerList: SeriesMarker<Time>[] = data.signals
      .filter((s) => byDate.has(s.date) && s.type !== "neutral")
      .map((s) => ({
        time: toTime(byDate.get(s.date)!.time),
        position: s.type === "buy" ? "belowBar" : "aboveBar",
        shape: s.type === "buy" ? "arrowUp" : "arrowDown",
        color: s.type === "buy" ? upColor : downColor,
        text: s.type === "buy" ? "B" : "S",
      }));
    r.markers.setMarkers(markerList);
    r.chart.timeScale().fitContent();
  }, [data, upColor, downColor]);

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
      const candle = data.candles.find((c) =>
        target ? c.time === target : toTime(c.time) === param.time,
      );
      if (!candle) {
        setLegend("");
        return;
      }
      setLegend(
        `O ${fmtPrice(candle.open)}  H ${fmtPrice(candle.high)}  L ${fmtPrice(candle.low)}  C ${fmtPrice(candle.close)}`,
      );
    };
    r.chart.subscribeCrosshairMove(handler);
    return () => r.chart.unsubscribeCrosshairMove(handler);
  }, [data]);

  return (
    <div className="chart-host">
      <div className="chart-hint">
        {alertMode ? "點擊圖表價位以建立到價警示（Esc 取消）" : legend}
      </div>
      <div ref={containerRef} className="lw-container" style={alertMode ? { cursor: "crosshair" } : undefined} />
    </div>
  );
}
