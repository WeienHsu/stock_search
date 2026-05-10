from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
from typing import Any, Literal

import streamlit as st

from src.repositories.watchlist_repo import get_watchlist
from src.ui.nav.page_keys import BACKTEST, DASHBOARD, LABEL_BY_KEY, SCANNER, SETTINGS, TODAY, WORKSTATION
from src.ui.nav.ticker_index import TickerMatch, build_ticker_index, format_ticker_match, fuzzy_ticker_matches

_SETTINGS_PATH = Path(__file__).parents[3] / "config" / "default_settings.json"


@dataclass(frozen=True)
class CommandResult:
    kind: Literal["ticker", "page"]
    label: str
    description: str
    ticker: str = ""
    page_key: str = ""
    score: float = 0.0


_PAGE_COMMANDS = [
    (TODAY, "Today", "今日摘要"),
    (DASHBOARD, "Dashboard", "股票頁"),
    (WORKSTATION, "綜合看盤", "分時 / K 線 / 自選"),
    (SCANNER, "掃描器", "策略掃描"),
    (BACKTEST, "回測", "策略回測"),
    (SETTINGS, "設定", "偏好與 API"),
]


def render_command_palette(user_id: str) -> None:
    watchlist = _watchlist(user_id)
    defaults = _defaults()
    payload = _client_palette_payload(watchlist, defaults)
    st.html(
        _command_palette_markup(payload),
        width="content",
    )
    st.html(
        _command_palette_controller_script(),
        width="content",
        unsafe_allow_javascript=True,
    )


def build_command_sections(
    query: str,
    watchlist: list[dict[str, Any]],
    defaults: list[dict[str, Any]],
) -> dict[str, list[CommandResult]]:
    index = build_ticker_index(watchlist, defaults)
    clean_query = query.strip()
    if not clean_query:
        return {"Pages": page_command_results(clean_query)}

    ticker_results = [_ticker_result(match) for match in fuzzy_ticker_matches(clean_query, index, limit=8)]
    page_results = page_command_results(clean_query)
    sections: dict[str, list[CommandResult]] = {}
    if ticker_results:
        sections["Tickers"] = ticker_results
    if page_results:
        sections["Pages"] = page_results
    return sections


def page_command_results(query: str, *, limit: int = 6) -> list[CommandResult]:
    clean_query = query.strip().lower()
    results: list[CommandResult] = []
    for page_key, label, description in _PAGE_COMMANDS:
        haystack = f"{page_key} {label} {description} {LABEL_BY_KEY[page_key]}".lower()
        if clean_query and clean_query not in haystack:
            continue
        results.append(CommandResult(
            kind="page",
            label=f"{LABEL_BY_KEY[page_key]} — {description}",
            description=f"前往 /{page_key}",
            page_key=page_key,
            score=1.0,
        ))
    return results[:limit]


def _ticker_result(match: TickerMatch) -> CommandResult:
    source = "自選清單" if match.source == "watchlist" else "預設清單"
    return CommandResult(
        kind="ticker",
        label=format_ticker_match(match),
        description=f"{source}；前往 Dashboard",
        ticker=match.ticker,
        score=match.score,
    )


def _watchlist(user_id: str) -> list[dict[str, Any]]:
    try:
        return get_watchlist(user_id)
    except Exception:
        return []


def _defaults() -> list[dict[str, Any]]:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("watchlist_defaults", []))


def _client_palette_payload(watchlist: list[dict[str, Any]], defaults: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tickers": build_ticker_index(watchlist, defaults),
        "pages": [
            {
                "pageKey": page_key,
                "label": label,
                "description": description,
                "navLabel": LABEL_BY_KEY[page_key],
            }
            for page_key, label, description in _PAGE_COMMANDS
        ],
    }


def _command_palette_markup(payload: dict[str, Any]) -> str:
    payload_json = escape(json.dumps(payload, ensure_ascii=False), quote=False)
    dashboard_key = escape(DASHBOARD, quote=True)
    return f"""
        <style>{_COMMAND_PALETTE_CSS}</style>
        <div id="stock-search-command-palette" data-open="0" data-dashboard-key="{dashboard_key}">
          <div class="sscp-panel" role="dialog" aria-modal="true" aria-label="Command Palette">
            <input class="sscp-input" aria-label="搜尋股票或頁面" placeholder="輸入股票代號、名稱或頁面，例如 tsmc、2330、settings" />
            <div class="sscp-results" role="listbox"></div>
            <template data-command-palette-payload>{payload_json}</template>
          </div>
        </div>
        """


def _command_palette_controller_script() -> str:
    return """
        <script>
        (function() {
          const hostWindow = window.parent && window.parent !== window ? window.parent : window;
          const root = hostWindow.document || document;

          function readPayload(overlay) {
            if (overlay.__sscpPayload) return overlay.__sscpPayload;
            const template = overlay.querySelector("[data-command-palette-payload]");
            const rawPayload = template && template.content ? template.content.textContent : (template && template.textContent) || "{}";
            try {
              overlay.__sscpPayload = JSON.parse(rawPayload || "{}");
            } catch (_) {
              overlay.__sscpPayload = {};
            }
            return overlay.__sscpPayload;
          }

          function setupPalette(overlay) {
            if (!overlay || overlay.__sscpReady) return;
            const payload = readPayload(overlay);
            const pages = payload.pages || [];
            const tickers = payload.tickers || [];
            const dashboardKey = overlay.dataset.dashboardKey || "dashboard";
            const input = overlay.querySelector(".sscp-input");
            const results = overlay.querySelector(".sscp-results");
            let activeIndex = 0;
            let currentResults = [];

            function scoreTicker(query, item) {
              if (!query) return 0;
              const ticker = String(item.ticker || "").toUpperCase();
              const compact = ticker.split(".")[0];
              const aliases = (item.aliases || []).map(function(alias) { return String(alias); });
              const haystack = [ticker, compact, item.name || ""].concat(aliases).join(" ").toUpperCase();
              if (ticker === query || compact === query) return 3.0;
              if (ticker.startsWith(query) || compact.startsWith(query)) return 2.7;
              if (ticker.includes(query) || compact.includes(query)) return 2.2;
              if (haystack.includes(query)) return 1.8;
              return 0;
            }

            function tickerMatches(query) {
              if (!query) return [];
              return tickers
                .map(function(item) { return [scoreTicker(query, item), item]; })
                .filter(function(row) { return row[0] > 0; })
                .sort(function(a, b) {
                  if (b[0] !== a[0]) return b[0] - a[0];
                  if (a[1].source !== b[1].source) return a[1].source === "watchlist" ? -1 : 1;
                  return String(a[1].ticker).localeCompare(String(b[1].ticker));
                })
                .slice(0, 8)
                .map(function(row) { return Object.assign({ kind: "ticker", score: row[0] }, row[1]); });
            }

            function pageMatches(query) {
              return pages.filter(function(page) {
                if (!query) return true;
                const haystack = [page.pageKey, page.label, page.description, page.navLabel].join(" ").toLowerCase();
                return haystack.includes(query.toLowerCase());
              }).slice(0, 8).map(function(page) {
                return Object.assign({ kind: "page" }, page);
              });
            }

            function navigate(pageKey, ticker) {
              const url = new URL(hostWindow.location.href);
              url.searchParams.set("page", pageKey);
              if (ticker) url.searchParams.set("ticker", ticker);
              else url.searchParams.delete("ticker");
              hostWindow.location.assign(url.toString());
            }

            function activate(result) {
              if (!result) return;
              if (result.kind === "ticker") navigate(dashboardKey, result.ticker);
              else navigate(result.pageKey, "");
            }

            function appendText(parent, className, text) {
              const node = root.createElement("span");
              node.className = className;
              node.textContent = text;
              parent.appendChild(node);
            }

            function appendSection(title, items) {
              const section = root.createElement("div");
              section.className = "sscp-section";
              const heading = root.createElement("div");
              heading.className = "sscp-title";
              heading.textContent = title;
              section.appendChild(heading);
              items.forEach(function(item) {
                const button = root.createElement("button");
                const index = currentResults.indexOf(item);
                button.className = "sscp-item";
                button.type = "button";
                button.dataset.active = index === activeIndex ? "1" : "0";
                const label = item.kind === "ticker"
                  ? String(item.ticker || "") + (item.name ? " — " + item.name : "")
                  : String(item.navLabel || "") + " — " + String(item.description || "");
                const desc = item.kind === "ticker"
                  ? (item.source === "watchlist" ? "自選清單" : "預設清單")
                  : "/" + String(item.pageKey || "");
                appendText(button, "sscp-label", label);
                appendText(button, "sscp-desc", desc);
                button.addEventListener("click", function() { activate(item); });
                section.appendChild(button);
              });
              results.appendChild(section);
            }

            function render() {
              const query = String(input.value || "").trim();
              const tickerResults = tickerMatches(query.toUpperCase());
              const pageResults = pageMatches(query);
              currentResults = tickerResults.concat(pageResults);
              activeIndex = Math.min(activeIndex, Math.max(currentResults.length - 1, 0));
              results.replaceChildren();
              if (tickerResults.length) appendSection("股票", tickerResults);
              if (pageResults.length) appendSection("頁面", pageResults);
              if (!currentResults.length) {
                const empty = root.createElement("div");
                empty.className = "sscp-empty";
                empty.textContent = "找不到符合的股票或頁面";
                results.appendChild(empty);
              }
            }

            overlay.__sscpOpen = function() {
              overlay.dataset.open = "1";
              input.value = "";
              activeIndex = 0;
              render();
              setTimeout(function() { input.focus(); }, 0);
            };
            overlay.__sscpClose = function() {
              overlay.dataset.open = "0";
            };

            overlay.addEventListener("click", function(event) {
              if (event.target === overlay) overlay.__sscpClose();
            });
            input.addEventListener("input", function() {
              activeIndex = 0;
              render();
            });
            overlay.addEventListener("keydown", function(event) {
              if (event.key === "Escape") {
                event.preventDefault();
                overlay.__sscpClose();
                return;
              }
              if (event.key === "ArrowDown") {
                event.preventDefault();
                activeIndex = Math.min(activeIndex + 1, Math.max(currentResults.length - 1, 0));
                render();
                return;
              }
              if (event.key === "ArrowUp") {
                event.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
                render();
                return;
              }
              if (event.key === "Enter") {
                event.preventDefault();
                activate(currentResults[activeIndex]);
              }
            });
            overlay.__sscpReady = true;
          }

          function openPalette() {
            const overlay = root.getElementById("stock-search-command-palette");
            if (!overlay) return;
            setupPalette(overlay);
            if (overlay.__sscpOpen) overlay.__sscpOpen();
          }

          window.addEventListener("stock-search:open-command-palette", openPalette);
          if (hostWindow !== window) {
            hostWindow.addEventListener("stock-search:open-command-palette", openPalette);
          }
        })();
        </script>
        """


_COMMAND_PALETTE_CSS = """
#stock-search-command-palette {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  display: none;
  align-items: flex-start;
  justify-content: center;
  padding-top: min(12vh, 96px);
  background: rgba(17, 20, 24, 0.42);
}
#stock-search-command-palette[data-open="1"] {
  display: flex;
}
.sscp-panel {
  width: min(720px, calc(100vw - 32px));
  max-height: min(76vh, 720px);
  overflow: hidden;
  border: 1px solid rgba(138, 126, 118, 0.38);
  border-radius: 10px;
  background: #F5F2EE;
  color: #4A4540;
  box-shadow: 0 24px 80px rgba(24, 20, 17, 0.28);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang TC", "Microsoft JhengHei", "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  .sscp-panel {
    background: #252830;
    color: #E8EAF0;
    border-color: rgba(111, 120, 136, 0.55);
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.52);
  }
}
.sscp-input {
  box-sizing: border-box;
  width: 100%;
  height: 52px;
  border: 0;
  border-bottom: 1px solid rgba(138, 126, 118, 0.35);
  padding: 0 18px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 16px;
  outline: none;
}
.sscp-input::placeholder {
  color: #7C7672;
  opacity: 1;
}
@media (prefers-color-scheme: dark) {
  .sscp-input {
    border-bottom-color: rgba(111, 120, 136, 0.45);
  }
  .sscp-input::placeholder {
    color: #9AA0B0;
  }
}
.sscp-results {
  max-height: calc(min(76vh, 720px) - 52px);
  overflow-y: auto;
  padding: 10px;
}
.sscp-section {
  padding: 8px 0;
}
.sscp-title {
  padding: 0 8px 6px;
  color: #665F59;
  font-size: 12px;
  font-weight: 650;
}
@media (prefers-color-scheme: dark) {
  .sscp-title {
    color: #9AA0B0;
  }
}
.sscp-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  font: inherit;
}
.sscp-item:hover,
.sscp-item[data-active="1"] {
  background: #E5DFD7;
}
@media (prefers-color-scheme: dark) {
  .sscp-item:hover,
  .sscp-item[data-active="1"] {
    background: #303642;
  }
}
.sscp-label {
  font-weight: 650;
}
.sscp-desc {
  flex: 0 0 auto;
  color: #665F59;
  font-size: 12px;
}
@media (prefers-color-scheme: dark) {
  .sscp-desc {
    color: #9AA0B0;
  }
}
.sscp-empty {
  padding: 16px 10px;
  color: #665F59;
  font-size: 13px;
}
@media (prefers-color-scheme: dark) {
  .sscp-empty {
    color: #9AA0B0;
  }
}
"""
