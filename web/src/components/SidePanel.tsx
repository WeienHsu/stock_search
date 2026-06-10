import { useState } from "react";
import { api } from "../api";
import { usePoll } from "../usePoll";
import { fmtPrice, fmtTime } from "../format";
import type { Alert, Quote } from "../types";

interface Props {
  symbol: string;
  quote?: Quote;
  alerts: Alert[];
  refreshAlerts: () => void;
  alertMode: boolean;
  setAlertMode: (on: boolean) => void;
  pendingPrice: number | null;
  clearPendingPrice: () => void;
}

export function SidePanel(props: Props) {
  const [tab, setTab] = useState<"alerts" | "inbox">("alerts");
  const { data: inboxData, refresh: refreshInbox } = usePoll(() => api.inbox(), 60_000);
  const unread = inboxData?.unread ?? 0;

  return (
    <aside className="side">
      <div className="side-tabs">
        <button className={tab === "alerts" ? "active" : ""} onClick={() => setTab("alerts")}>
          到價警示
        </button>
        <button className={tab === "inbox" ? "active" : ""} onClick={() => setTab("inbox")}>
          通知中心{unread > 0 ? ` (${unread})` : ""}
        </button>
      </div>
      <div className="side-body">
        {tab === "alerts" ? (
          <AlertsTab {...props} />
        ) : (
          <InboxTab
            messages={inboxData?.messages ?? []}
            onRead={(id) => api.markRead(id).then(refreshInbox)}
          />
        )}
      </div>
    </aside>
  );
}

function AlertsTab({
  symbol,
  quote,
  alerts,
  refreshAlerts,
  alertMode,
  setAlertMode,
  pendingPrice,
  clearPendingPrice,
}: Props) {
  const [threshold, setThreshold] = useState("");
  const { data: events } = usePoll(() => api.alertEvents(20), 30_000);

  const effectiveThreshold = pendingPrice != null ? pendingPrice.toFixed(2) : threshold;

  const create = async () => {
    const value = parseFloat(effectiveThreshold);
    if (!Number.isFinite(value) || !symbol) return;
    const direction = quote && value >= quote.price ? "above" : "below";
    await api.createAlert(symbol, direction, value);
    setThreshold("");
    clearPendingPrice();
    setAlertMode(false);
    refreshAlerts();
  };

  return (
    <>
      <div className="alert-form">
        <div className="full" style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <strong>{symbol || "—"}</strong>
          <span className="num" style={{ color: "var(--text-dim)" }}>
            現價 {fmtPrice(quote?.price)}
          </span>
        </div>
        <input
          className="num"
          placeholder="目標價"
          value={effectiveThreshold}
          onChange={(e) => {
            clearPendingPrice();
            setThreshold(e.target.value);
          }}
        />
        <button onClick={create}>建立警示</button>
        <button
          className={`full ${alertMode ? "active" : ""}`}
          onClick={() => setAlertMode(!alertMode)}
        >
          {alertMode ? "取消圖表選價" : "在圖表上點選價位"}
        </button>
      </div>

      {alerts.map((alert) => (
        <div key={alert.id} className={`alert-row ${alert.enabled ? "" : "disabled"}`}>
          <span className="ticker">{alert.ticker}</span>
          <span className="cond num">
            {alert.direction === "above" ? "≥" : "≤"} {fmtPrice(alert.threshold)}
          </span>
          {alert.triggered_at && <span className="badge triggered">已觸發</span>}
          <span className="right">
            <button
              className="ghost"
              title={alert.enabled ? "停用" : "啟用"}
              onClick={() =>
                api.setAlertEnabled(alert.id, !alert.enabled).then(refreshAlerts)
              }
            >
              {alert.enabled ? "⏸" : "▶"}
            </button>
            <button
              className="ghost"
              title="刪除"
              onClick={() => api.deleteAlert(alert.id).then(refreshAlerts)}
            >
              ✕
            </button>
          </span>
        </div>
      ))}
      {alerts.length === 0 && <div className="empty-note">尚無警示</div>}

      {events && events.length > 0 && (
        <>
          <div className="panel-title" style={{ borderTop: "1px solid var(--border)", marginTop: 10 }}>
            觸發紀錄
          </div>
          {events.map((event) => (
            <div key={event.id} className="event-row">
              <div>
                <strong>{event.ticker}</strong>{" "}
                {String(event.payload["message"] ?? event.event_type)}
              </div>
              <div className="time num">{fmtTime(event.created_at)}</div>
            </div>
          ))}
        </>
      )}
    </>
  );
}

function InboxTab({
  messages,
  onRead,
}: {
  messages: { id: string; subject: string; body: string; read_at: number | null; created_at: number }[];
  onRead: (id: string) => void;
}) {
  if (messages.length === 0) return <div className="empty-note">沒有通知</div>;
  return (
    <>
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`inbox-row ${msg.read_at ? "" : "unread"}`}
          onClick={() => !msg.read_at && onRead(msg.id)}
        >
          <div className="subject">{msg.subject}</div>
          <div className="body">{msg.body}</div>
          <div className="time num">{fmtTime(msg.created_at)}</div>
        </div>
      ))}
    </>
  );
}
