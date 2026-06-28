(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const storageKey = "nexora-theme";

  const path = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
  const isDashboard = path === "/dashboard" || path.startsWith("/dashboard/");
  const isAdmin = path === "/admin" || path.startsWith("/admin/");
  const isAuth = ["/login", "/register", "/forgot-password", "/reset-password"].some((p) => path === p || path.startsWith(p + "/"));

  if (isDashboard) body.classList.add("nx-page-dashboard");
  if (isAdmin) body.classList.add("nx-page-admin");
  if (isAuth) body.classList.add("nx-page-auth");

  function getTheme() {
    try {
      return localStorage.getItem(storageKey) === "light" ? "light" : "dark";
    } catch (_) {
      return "dark";
    }
  }

  function applyTheme(theme) {
    const safe = theme === "light" ? "light" : "dark";
    root.setAttribute("data-theme", safe);
    try { localStorage.setItem(storageKey, safe); } catch (_) {}
    document.querySelectorAll(".theme-toggle, .nx-theme-toggle").forEach((btn) => {
      btn.setAttribute("aria-label", safe === "light" ? "Switch to dark mode" : "Switch to light mode");
      if (btn.classList.contains("nx-theme-toggle")) btn.textContent = safe === "light" ? "☀" : "◐";
    });
  }

  applyTheme(getTheme());

  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".theme-toggle, .nx-theme-toggle");
    if (!btn) return;
    event.preventDefault();
    applyTheme(root.getAttribute("data-theme") === "light" ? "dark" : "light");
  });

  function ensureThemeToggle() {
    if (document.querySelector(".theme-toggle, .nx-theme-toggle")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nx-theme-toggle";
    btn.textContent = root.getAttribute("data-theme") === "light" ? "☀" : "◐";
    btn.style.position = "fixed";
    btn.style.top = "18px";
    btn.style.insetInlineEnd = "18px";
    btn.style.zIndex = "120";
    document.body.appendChild(btn);
  }

  ensureThemeToggle();

  function cleanLegacyVisualLayers() {
    const selectors = [
      ".nx-repair-sidebar",
      ".nx-repair-top-strip",
      ".nx-repair-dashboard-grid",
      ".nx-pro-dashboard-grid",
      ".nx-market-panel",
      ".nx-health-strip",
      ".nx-pro-market-strip",
      ".nx-premium-sidebar",
      ".nx-premium-topbar",
      ".nx-legacy-marketbar",
      ".nx-duplicate-marketbar",
      ".nx-dashboard-sidebar",
      ".nx-admin-sidebar"
    ];
    document.querySelectorAll(selectors.join(",")).forEach((node) => node.remove());
  }

  cleanLegacyVisualLayers();

  const dashboardLinks = [
    ["Dashboard", "/dashboard"],
    ["My Plan", "#pricing"],
    ["Signals", "#signals"],
    ["Auto Trading", "#auto-trading"],
    ["Referrals", "#referrals"],
    ["Payments", "/payment"],
    ["Invoices", "/invoice-history"],
    ["Profile", "#profile"],
    ["Settings", "#settings"],
    ["Logout", "/logout"]
  ];

  const adminLinks = [
    ["Admin Overview", "/admin"],
    ["Users", "#users"],
    ["Subscriptions", "#subscriptions"],
    ["Payments", "#payments"],
    ["Manual Payments", "#manual-payments"],
    ["Repair Pro 2Y", "#repair-pro-2y"],
    ["System Health", "/admin/system-health"],
    ["Settings", "#settings"],
    ["Logout", "/logout"]
  ];

  function buildSidebar(kind) {
    if (!(isDashboard || isAdmin)) return;
    if (document.querySelector(".nx-final-sidebar")) return;
    body.classList.add("nx-has-sidebar");

    const sidebar = document.createElement("aside");
    sidebar.className = "nx-final-sidebar";
    const links = kind === "admin" ? adminLinks : dashboardLinks;
    sidebar.innerHTML = `
      <div class="nx-final-brand">
        <strong>NEXORA</strong>
        <span>${kind === "admin" ? "Control Center" : "AI Signal Hunter"}</span>
      </div>
      <nav class="nx-final-nav">
        ${links.map(([label, href], i) => `<a href="${href}" class="${i === 0 ? "active" : ""}">${label}</a>`).join("")}
      </nav>
      <div class="nx-sidebar-note">
        <strong>${kind === "admin" ? "Admin Tools" : "Account Console"}</strong>
        ${kind === "admin" ? "Monitor users, payments and system status." : "Track subscription, Telegram and signal status."}
      </div>
    `;
    document.body.prepend(sidebar);
  }

  buildSidebar(isAdmin ? "admin" : "dashboard");

  const marketFallback = {
    BTCUSDT: { label: "BTC / USDT", icon: "₿", cls: "btc", price: "68,542.10", change: "+1.82" },
    ETHUSDT: { label: "ETH / USDT", icon: "Ξ", cls: "eth", price: "3,728.45", change: "+2.45" },
    SOLUSDT: { label: "SOL / USDT", icon: "S", cls: "sol", price: "162.85", change: "+3.21" },
    BNBUSDT: { label: "BNB / USDT", icon: "B", cls: "bnb", price: "601.75", change: "-0.35" }
  };

  const symbols = Object.keys(marketFallback);
  const cache = new Map();

  function formatPrice(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return value || "--";
    return n >= 1000
      ? n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  }

  function renderMarketBar() {
    if (!(isDashboard || isAdmin)) return;
    if (document.querySelector(".nx-final-marketbar")) return;

    const bar = document.createElement("section");
    bar.className = "nx-final-marketbar";
    bar.setAttribute("aria-label", "Live crypto market prices");
    bar.innerHTML = symbols.map((symbol) => {
      const item = marketFallback[symbol];
      return `
        <article class="nx-market-card" data-nx-symbol="${symbol}">
          <div class="nx-market-left">
            <span class="nx-coin ${item.cls}">${item.icon}</span>
            <span class="nx-symbol">${item.label}</span>
          </div>
          <strong class="nx-price">${item.price}</strong>
          <span class="nx-change ${String(item.change).startsWith("-") ? "down" : ""}">${item.change}%</span>
        </article>
      `;
    }).join("") + `<div class="nx-market-meta">Live <span class="nx-dot"></span></div>`;

    document.body.insertBefore(bar, document.body.firstChild.nextSibling);
  }

  function applyMarketValues(values) {
    symbols.forEach((symbol) => {
      const node = document.querySelector(`[data-nx-symbol="${symbol}"]`);
      if (!node) return;
      const fallback = marketFallback[symbol];
      const item = values[symbol] || cache.get(symbol) || fallback;
      const price = node.querySelector(".nx-price");
      const change = node.querySelector(".nx-change");
      if (price) price.textContent = formatPrice(item.price || item.lastPrice || fallback.price);
      if (change) {
        const ch = Number(item.change ?? item.priceChangePercent ?? fallback.change);
        const txt = Number.isFinite(ch) ? `${ch >= 0 ? "+" : ""}${ch.toFixed(2)}%` : `${fallback.change}%`;
        change.textContent = txt;
        change.classList.toggle("down", txt.startsWith("-"));
      }
    });
  }

  async function refreshMarket() {
    if (!(isDashboard || isAdmin)) return;
    const fallbackValues = {};
    symbols.forEach((s) => fallbackValues[s] = cache.get(s) || marketFallback[s]);

    try {
      const url = `https://api.binance.us/api/v3/ticker/24hr?symbols=${encodeURIComponent(JSON.stringify(symbols))}`;
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error("market api failed");
      const data = await response.json();
      const values = {};
      data.forEach((row) => {
        if (!row || !row.symbol || !symbols.includes(row.symbol)) return;
        values[row.symbol] = {
          price: row.lastPrice,
          change: row.priceChangePercent
        };
        cache.set(row.symbol, values[row.symbol]);
      });
      applyMarketValues(values);
    } catch (_) {
      applyMarketValues(fallbackValues);
    }
  }

  renderMarketBar();
  refreshMarket();
  if (isDashboard || isAdmin) window.setInterval(refreshMarket, 15000);

  function injectDashboardVisuals() {
    if (!isDashboard || document.querySelector(".nx-final-dashboard-grid")) return;
    const hero = document.querySelector(".hero");
    const anchor = document.querySelector(".premium-status-grid") || hero;
    if (!anchor || !anchor.parentNode) return;

    const grid = document.createElement("section");
    grid.className = "nx-final-dashboard-grid";
    grid.innerHTML = `
      <article class="nx-final-panel">
        <h3>Account Health</h3>
        <div class="nx-health-ring"><strong>95%</strong></div>
        <div class="nx-check-list">
          <span>Account Verified</span>
          <span>Telegram Connected</span>
          <span>Risk Settings Active</span>
          <span>Subscription Checked</span>
        </div>
      </article>
      <article class="nx-final-panel">
        <h3>Recent Signals</h3>
        <div class="nx-signal-row"><strong>BTC/USDT</strong><span class="nx-pill">LONG</span><span>R/R 1:2.4</span><small>Live scan</small></div>
        <div class="nx-signal-row"><strong>ETH/USDT</strong><span class="nx-pill">WATCH</span><span>Structure</span><small>Market filter</small></div>
        <div class="nx-signal-row"><strong>SOL/USDT</strong><span class="nx-pill">WAIT</span><span>S/R check</span><small>Hunter mode</small></div>
      </article>
      <article class="nx-final-panel">
        <h3>Quick Actions</h3>
        <div class="nx-quick-grid">
          <a href="/payment">Upgrade Plan</a>
          <a href="/manual-payment">Manual Pay</a>
          <a href="#referrals">Invite & Earn</a>
          <a href="/bot-check">Bot Check</a>
        </div>
      </article>
    `;
    anchor.parentNode.insertBefore(grid, anchor.nextSibling);
  }

  injectDashboardVisuals();

})();
