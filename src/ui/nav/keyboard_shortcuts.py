from __future__ import annotations

import json

import streamlit as st

from src.ui.nav.page_keys import DASHBOARD

_KNOWN_PAGE_PATHS = [
    "today",
    "dashboard",
    "workstation",
    "market",
    "scanner",
    "backtest",
    "risk",
    "alerts",
    "settings",
    "admin",
]

_SHORTCUT_TARGETS = {
    "d": DASHBOARD,
    "s": DASHBOARD,
}


def inject_shortcuts() -> None:
    """Inject minimal keyboard shortcuts for app navigation and sidebar search."""
    st.html(
        _shortcut_script(),
        width="content",
        unsafe_allow_javascript=True,
    )


def _shortcut_script() -> str:
    known_paths = json.dumps(_KNOWN_PAGE_PATHS)
    targets = json.dumps(_SHORTCUT_TARGETS)
    return f"""
<script>
(function() {{
  if (window.__stockSearchShortcutsInstalled) return;
  window.__stockSearchShortcutsInstalled = true;

  const knownPagePaths = new Set({known_paths});
  const shortcutTargets = {targets};
  let pendingGAt = 0;

  function isTypingTarget(target) {{
    if (!target) return false;
    const tagName = String(target.tagName || "").toLowerCase();
    return target.isContentEditable || ["input", "textarea", "select"].includes(tagName);
  }}

  function focusQuickSearch() {{
    const sidebar = document.querySelector('[data-testid="stSidebar"]') || document;
    const input =
      sidebar.querySelector('input[placeholder="輸入代號或名稱"]') ||
      sidebar.querySelector('input[aria-label="搜尋股票"]') ||
      sidebar.querySelector('input');
    if (!input) return;
    input.focus();
    if (typeof input.select === "function") input.select();
  }}

  function pageUrl(pageKey) {{
    const url = new URL(window.location.href);
    const parts = url.pathname.split("/").filter(Boolean);
    if (parts.length && knownPagePaths.has(parts[parts.length - 1])) {{
      parts.pop();
    }}
    parts.push(pageKey);
    url.pathname = "/" + parts.join("/");
    url.search = "";
    return url.toString();
  }}

  function findNavLink(pageKey) {{
    const links = Array.from(document.querySelectorAll('a[href]'));
    return links.find(function(link) {{
      try {{
        const url = new URL(link.getAttribute("href"), window.location.href);
        const parts = url.pathname.split("/").filter(Boolean);
        return parts.length && parts[parts.length - 1] === pageKey;
      }} catch (_) {{
        return false;
      }}
    }}) || null;
  }}

  function navigateTo(pageKey) {{
    const link = findNavLink(pageKey);
    if (link) {{
      link.click();
      return;
    }}
    window.location.assign(pageUrl(pageKey));
  }}

  document.addEventListener("keydown", function(event) {{
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
    if (isTypingTarget(event.target)) return;

    const key = String(event.key || "").toLowerCase();
    const now = Date.now();

    if (key === "/") {{
      event.preventDefault();
      focusQuickSearch();
      pendingGAt = 0;
      return;
    }}

    if (key === "g") {{
      pendingGAt = now;
      return;
    }}

    if (pendingGAt && now - pendingGAt < 900 && Object.prototype.hasOwnProperty.call(shortcutTargets, key)) {{
      event.preventDefault();
      const target = shortcutTargets[key];
      pendingGAt = 0;
      navigateTo(target);
      return;
    }}

    if (pendingGAt && now - pendingGAt >= 900) {{
      pendingGAt = 0;
    }}
  }});
}})();
</script>
"""
