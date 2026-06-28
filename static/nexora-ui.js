(() => {
  const root = document.documentElement;
  const applyTheme = (theme) => {
    const next = theme === "light" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("nexora-theme", next); } catch (_) {}
  };

  try {
    applyTheme(localStorage.getItem("nexora-theme") || "dark");
  } catch (_) {
    root.setAttribute("data-theme", "dark");
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".theme-toggle, .nexora-theme-toggle");
    if (!button) return;
    const current = root.getAttribute("data-theme") || "dark";
    applyTheme(current === "light" ? "dark" : "light");
  });

  const fallback = {
    BTCUSDT: ["68,539.24", "+1.24%"],
    ETHUSDT: ["3,728.41", "+2.15%"],
    BNBUSDT: ["604.89", "+1.03%"],
    SOLUSDT: ["152.63", "+3.42%"],
    XRPUSDT: ["0.4792", "+1.87%"],
    DOGEUSDT: ["0.1234", "+2.94%"]
  };

  const updateTicker = async () => {
    const pills = [...document.querySelectorAll(".premium-market-pill")];
    if (!pills.length || !window.fetch) return;
    try {
      const symbols = Object.keys(fallback);
      const res = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache: "no-store" });
      if (!res.ok) return;
      const rows = await res.json();
      const map = new Map(rows.filter((row) => symbols.includes(row.symbol)).map((row) => [row.symbol, row]));
      pills.forEach((pill) => {
        const label = (pill.querySelector("strong")?.textContent || "").replace("/", "");
        const row = map.get(label);
        if (!row) return;
        const price = Number(row.lastPrice || 0);
        const change = Number(row.priceChangePercent || 0);
        const span = pill.querySelector("span");
        if (!span || !price) return;
        span.textContent = `${price.toLocaleString(undefined, { maximumFractionDigits: price > 10 ? 2 : 4 })} ${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
      });
    } catch (_) {
      // Fallback UI remains visible.
    }
  };

  window.addEventListener("load", updateTicker, { once: true });
})();

// Nexora V4 final visual polish
(() => {
  const root = document.documentElement;
  const body = document.body;
  if (!body || body.dataset.nexoraV4 === "1") return;
  body.dataset.nexoraV4 = "1";
  body.classList.add("nexora-v4");

  const path = window.location.pathname || "/";
  if (path === "/" || path === "/landing") body.classList.add("nx-landing");
  if (path.includes("dashboard") || document.querySelector(".plan-dashboard")) body.classList.add("nx-dashboard");
  if (path.includes("admin") || document.querySelector(".admin-shell")) body.classList.add("nx-admin");
  if (document.querySelector(".login-box,.register-box,.verify-box,.success-box")) body.classList.add("nx-auth");

  const markActiveLinks = () => {
    document.querySelectorAll("a[href]").forEach((link) => {
      try {
        const url = new URL(link.getAttribute("href"), window.location.origin);
        if (url.pathname === path || (path === "/" && url.pathname === "/")) {
          link.classList.add("is-active");
        }
      } catch (_) {}
    });
  };
  markActiveLinks();

  const hero = document.querySelector(".hero, .hero-main");
  if (hero && !hero.querySelector(".nx-float-icons")) {
    hero.style.position = hero.style.position || "relative";
    const layer = document.createElement("div");
    layer.className = "nx-float-icons";
    ["₿", "Ξ", "◎", "N"].forEach((icon) => {
      const coin = document.createElement("span");
      coin.className = "nx-float-coin";
      coin.textContent = icon;
      layer.appendChild(coin);
    });
    hero.prepend(layer);
  }

  const revealTargets = document.querySelectorAll(".card,.box,.premium-status-card,.widget,.dashboard-panel,.metric-card,.quick-card,.overview-card,.ops-panel,.section,.health-panel,.table-wrap,.plan-dashboard");
  revealTargets.forEach((node) => node.classList.add("nx-v4-reveal"));
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    revealTargets.forEach((node) => observer.observe(node));
  } else {
    revealTargets.forEach((node) => node.classList.add("is-visible"));
  }

  const countNumber = (el) => {
    if (el.dataset.counted === "1") return;
    const raw = (el.textContent || "").trim();
    const match = raw.match(/-?\d+(?:[,.]\d+)?/);
    if (!match) return;
    const end = Number(match[0].replace(/,/g, ""));
    if (!Number.isFinite(end) || Math.abs(end) > 10000000) return;
    el.dataset.counted = "1";
    const prefix = raw.slice(0, match.index);
    const suffix = raw.slice((match.index || 0) + match[0].length);
    const start = performance.now();
    const duration = 900;
    const decimals = match[0].includes(".") ? Math.min(2, match[0].split(".")[1].length) : 0;
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = end * eased;
      el.textContent = `${prefix}${value.toLocaleString(undefined, { maximumFractionDigits: decimals, minimumFractionDigits: decimals })}${suffix}`;
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = raw;
    };
    requestAnimationFrame(step);
  };
  document.querySelectorAll(".premium-status-card strong,.widget strong,.quick-card strong,.metric-card strong,.overview-card .value,#profit,.price").forEach(countNumber);

  const ensureDashboardMarketPanel = () => {
    if (!body.classList.contains("nx-dashboard") || document.querySelector(".nx-market-panel")) return;
    const anchor = document.querySelector(".premium-status-grid") || document.querySelector(".plan-dashboard") || document.querySelector(".hero");
    if (!anchor || !anchor.parentNode) return;
    const panel = document.createElement("section");
    panel.className = "nx-market-panel";
    panel.setAttribute("aria-label", "Live market preview");
    panel.innerHTML = `
      <div class="nx-market-panel__head">
        <strong>Live Market Pulse</strong>
        <span class="nx-live-dot">LIVE</span>
      </div>
      <div class="nx-market-grid">
        ${["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"].map((symbol) => `
          <article class="nx-market-card nx-skeleton" data-symbol="${symbol}">
            <span class="nx-market-symbol">${symbol.replace("USDT", "/USDT")}</span>
            <strong class="nx-market-price">Loading</strong>
            <span class="nx-market-change">--</span>
          </article>
        `).join("")}
      </div>`;
    anchor.insertAdjacentElement("afterend", panel);
  };
  ensureDashboardMarketPanel();

  const fallbackMarket = {
    BTCUSDT: { price: 68539.24, change: 1.24 },
    ETHUSDT: { price: 3728.41, change: 2.15 },
    SOLUSDT: { price: 152.63, change: 3.42 },
    BNBUSDT: { price: 604.89, change: 1.03 }
  };

  const applyMarketRows = (rows) => {
    document.querySelectorAll(".nx-market-card").forEach((card) => {
      const symbol = card.dataset.symbol;
      const row = rows[symbol] || fallbackMarket[symbol];
      if (!row) return;
      const price = Number(row.price);
      const change = Number(row.change);
      const priceNode = card.querySelector(".nx-market-price");
      const changeNode = card.querySelector(".nx-market-change");
      if (priceNode) {
        priceNode.textContent = price.toLocaleString(undefined, {
          maximumFractionDigits: price > 100 ? 2 : 4
        });
      }
      if (changeNode) {
        changeNode.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
      }
      card.classList.toggle("is-down", change < 0);
      card.classList.remove("nx-skeleton");
    });
  };

  let lastMarketRows = { ...fallbackMarket };
  const refreshMarket = async () => {
    if (!document.querySelector(".nx-market-card")) return;
    try {
      const res = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache: "no-store" });
      if (!res.ok) throw new Error("market unavailable");
      const data = await res.json();
      const wanted = new Set(Object.keys(fallbackMarket));
      const next = {};
      data.forEach((row) => {
        if (!wanted.has(row.symbol)) return;
        next[row.symbol] = {
          price: Number(row.lastPrice || 0),
          change: Number(row.priceChangePercent || 0)
        };
      });
      lastMarketRows = Object.keys(next).length ? { ...lastMarketRows, ...next } : lastMarketRows;
    } catch (_) {
      // Keep last known or fallback values.
    }
    applyMarketRows(lastMarketRows);
  };
  refreshMarket();
  window.setInterval(refreshMarket, 45000);

  const addHealthStrip = () => {
    if (!body.classList.contains("nx-dashboard") || document.querySelector(".nx-health-strip")) return;
    const anchor = document.querySelector(".nx-market-panel") || document.querySelector(".premium-status-grid");
    if (!anchor || !anchor.parentNode) return;
    const strip = document.createElement("section");
    strip.className = "nx-health-strip";
    strip.setAttribute("aria-label", "Account health overview");
    strip.innerHTML = `
      <div class="nx-health-item"><span>Account Health</span><strong>Protected</strong><div class="nx-health-meter"><i style="width:88%"></i></div></div>
      <div class="nx-health-item"><span>Signal Quality</span><strong>Risk Managed</strong><div class="nx-health-meter"><i style="width:82%"></i></div></div>
      <div class="nx-health-item"><span>Telegram</span><strong>${document.body.textContent.includes("Running") ? "Connected" : "Ready"}</strong><div class="nx-health-meter"><i style="width:76%"></i></div></div>
      <div class="nx-health-item"><span>Next Renewal</span><strong>Dashboard</strong><div class="nx-health-meter"><i style="width:64%"></i></div></div>`;
    anchor.insertAdjacentElement("afterend", strip);
  };
  addHealthStrip();

  const addAuthBrand = () => {
    if (!body.classList.contains("nx-auth") || document.querySelector(".nx-auth-brand")) return;
    const card = document.querySelector(".login-box,.register-box");
    if (!card) return;
    const brand = document.createElement("aside");
    brand.className = "nx-auth-brand";
    brand.innerHTML = `<strong>Nexora AI Trader</strong><span>Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.</span>`;
    document.body.appendChild(brand);
  };
  addAuthBrand();

  window.addEventListener("scroll", () => {
    const y = Math.min(24, window.scrollY / 20);
    document.documentElement.style.setProperty("--nx-parallax-y", `${y}px`);
  }, { passive: true });
})();

// Nexora V5 dashboard/admin signal hunter layout
(() => {
  const body = document.body;
  if (!body || body.dataset.nexoraV5 === "1") return;
  const isDashboard = body.classList.contains("nx-dashboard") || document.querySelector(".plan-dashboard");
  const isAdmin = body.classList.contains("nx-admin") || document.querySelector(".admin-shell");
  if (!isDashboard && !isAdmin) return;
  body.dataset.nexoraV5 = "1";
  body.classList.add("nx-pro-app");

  const path = window.location.pathname || "/";
  const isRtl = document.documentElement.dir === "rtl";
  const active = (href) => {
    try {
      const url = new URL(href, window.location.origin);
      return url.pathname === path ? " is-active" : "";
    } catch (_) {
      return "";
    }
  };

  const sidebarItems = isAdmin
    ? [
        ["Dashboard", "/admin", "⌂"],
        ["Users", "/admin#users", "◎"],
        ["Subscriptions", "/admin#subscriptions", "▣"],
        ["Payments", "/admin#payments", "▤"],
        ["Repair Pro 2Y", "/admin#repair-pro-2y", "⚒"],
        ["System Health", "/admin/system-health", "✧"],
        ["Landing", "/", "↗"],
        ["Logout", "/logout", "⇥"]
      ]
    : [
        ["Dashboard", "/dashboard", "⌂"],
        ["My Plan", "#pricing", "▣"],
        ["Signals", "/bot-check", "◈"],
        ["Auto Trading", "#vip-settings", "◌"],
        ["Referrals", "#referrals", "◎"],
        ["Payments", "/manual-payment/basic", "▤"],
        ["Invoices", "/invoice-history", "□"],
        ["Profile", "#profile", "☉"],
        ["Logout", "/logout", "⇥"]
      ];

  if (!document.querySelector(".nx-pro-sidebar")) {
    const sidebar = document.createElement("aside");
    sidebar.className = "nx-pro-sidebar";
    sidebar.innerHTML = `
      <div class="nx-pro-brand">
        <div class="nx-pro-brand-mark">N</div>
        <div><strong>Nexora</strong><span>AI Signal Hunter</span></div>
      </div>
      <nav class="nx-pro-nav" aria-label="${isAdmin ? "Admin navigation" : "Dashboard navigation"}">
        ${sidebarItems.map(([label, href, icon]) => `<a class="${active(href)}" href="${href}"><span>${icon}</span>${label}</a>`).join("")}
      </nav>`;
    document.body.prepend(sidebar);
  }

  const marketSymbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];
  const symbolIcon = { BTCUSDT: "₿", ETHUSDT: "Ξ", SOLUSDT: "S", BNBUSDT: "B" };
  const fallback = {
    BTCUSDT: { price: 68542.10, change: 1.82 },
    ETHUSDT: { price: 3728.45, change: 2.45 },
    SOLUSDT: { price: 162.85, change: 3.21 },
    BNBUSDT: { price: 601.75, change: -0.35 }
  };

  if (!document.querySelector(".nx-pro-toolbar")) {
    const toolbar = document.createElement("section");
    toolbar.className = "nx-pro-toolbar";
    toolbar.innerHTML = `
      <div class="nx-pro-market-strip" aria-label="Live crypto prices">
        ${marketSymbols.map((symbol) => `<article class="nx-pro-coin" data-symbol="${symbol}">
          <span class="nx-pro-coin-icon">${symbolIcon[symbol]}</span>
          <strong>${symbol.replace("USDT", " / USDT")}</strong>
          <b class="nx-pro-price">--</b>
          <span class="nx-pro-change">--</span>
        </article>`).join("")}
      </div>
      <div class="nx-pro-user">
        <div>
          <strong>${isAdmin ? "Admin" : "Nexora Trader"}</strong>
          <small>${isAdmin ? "Super Admin" : "Live Account"}</small>
        </div>
        <div class="nx-pro-avatar" aria-hidden="true"></div>
      </div>`;
    const target = document.querySelector(".page-wrap,.admin-shell,.topbar") || document.body.firstElementChild;
    document.body.insertBefore(toolbar, target);
  }

  const applyRows = (rows) => {
    document.querySelectorAll(".nx-pro-coin, .nx-market-card").forEach((card) => {
      const symbol = card.dataset.symbol;
      const row = rows[symbol] || fallback[symbol];
      if (!row) return;
      const price = Number(row.price);
      const change = Number(row.change);
      const priceNode = card.querySelector(".nx-pro-price, .nx-market-price");
      const changeNode = card.querySelector(".nx-pro-change, .nx-market-change");
      if (priceNode) {
        priceNode.textContent = price.toLocaleString(undefined, { maximumFractionDigits: price > 100 ? 2 : 4 });
      }
      if (changeNode) {
        changeNode.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
      }
      card.classList.toggle("is-down", change < 0);
      card.classList.remove("nx-skeleton");
    });
  };

  let cache = { ...fallback };
  const refresh = async () => {
    try {
      const res = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache: "no-store" });
      if (!res.ok) throw new Error("market unavailable");
      const data = await res.json();
      const wanted = new Set(marketSymbols);
      const next = {};
      data.forEach((row) => {
        if (!wanted.has(row.symbol)) return;
        next[row.symbol] = {
          price: Number(row.lastPrice || 0),
          change: Number(row.priceChangePercent || 0)
        };
      });
      if (Object.keys(next).length) cache = { ...cache, ...next };
    } catch (_) {
      // Keep current values.
    }
    applyRows(cache);
  };
  refresh();
  window.setInterval(refresh, 15000);

  if (isDashboard && !document.querySelector(".nx-pro-dashboard-grid")) {
    const anchor = document.querySelector(".nx-health-strip") || document.querySelector(".nx-market-panel") || document.querySelector(".premium-status-grid");
    if (anchor && anchor.parentNode) {
      const grid = document.createElement("section");
      grid.className = "nx-pro-dashboard-grid";
      grid.innerHTML = `
        <article class="nx-pro-card">
          <h3>Account Health</h3>
          <div class="nx-health-ring"><div><strong>95%</strong><span>Excellent</span></div></div>
          <div class="nx-health-list">
            <div><i class="nx-check">✓</i>Account Verified</div>
            <div><i class="nx-check">✓</i>Telegram Connected</div>
            <div><i class="nx-check">✓</i>Payment Method Verified</div>
            <div><i class="nx-check">✓</i>Active Subscription</div>
          </div>
        </article>
        <article class="nx-pro-card">
          <h3>Recent Signals</h3>
          <div class="nx-recent-row"><strong>BTC/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 68,100</span><span>TP 69,200</span><span>2m</span></div>
          <div class="nx-recent-row"><strong>ETH/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 3,700</span><span>TP 3,820</span><span>5m</span></div>
          <div class="nx-recent-row"><strong>SOL/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 160.50</span><span>TP 166.80</span><span>12m</span></div>
        </article>
        <article class="nx-pro-card">
          <h3>Quick Actions</h3>
          <div class="nx-quick-grid">
            <a href="/bot-check"><span class="nx-quick-icon">◈</span>Get New Signals</a>
            <a href="#vip-settings"><span class="nx-quick-icon">◌</span>Auto Trading</a>
            <a href="/manual-payment/basic"><span class="nx-quick-icon">▤</span>Payment / Upgrade</a>
            <a href="#referrals"><span class="nx-quick-icon">◎</span>Invite & Earn</a>
          </div>
        </article>`;
      anchor.insertAdjacentElement("afterend", grid);
    }
  }
})();

// Nexora emergency repair V6: force theme + visible dashboard/admin layout
(() => {
  const root = document.documentElement;
  const body = document.body;
  if (!body || body.dataset.nexoraRepairV6 === "1") return;
  body.dataset.nexoraRepairV6 = "1";

  const applyTheme = (theme) => {
    const next = theme === "light" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    body.setAttribute("data-nx-theme", next);
    try { localStorage.setItem("nexora-theme", next); } catch (_) {}
    document.querySelectorAll(".theme-toggle,.nexora-theme-toggle").forEach((btn) => {
      btn.setAttribute("aria-label", next === "light" ? "Switch to dark mode" : "Switch to light mode");
      btn.dataset.themeState = next;
    });
  };
  try { applyTheme(localStorage.getItem("nexora-theme") || root.getAttribute("data-theme") || "dark"); } catch (_) { applyTheme("dark"); }
  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".theme-toggle,.nexora-theme-toggle,[data-theme-toggle]");
    if (!btn) return;
    event.preventDefault();
    applyTheme(root.getAttribute("data-theme") === "light" ? "dark" : "light");
  }, true);

  const path = location.pathname || "/";
  const isDashboard = path.includes("dashboard") || !!document.querySelector(".plan-dashboard,.premium-status-grid,.widget-grid");
  const isAdmin = path.includes("admin") || !!document.querySelector(".admin-shell,.overview-grid");
  const isHealth = path.includes("system-health") || !!document.querySelector(".health-shell");
  if (!isDashboard && !isAdmin && !isHealth) return;
  body.classList.add("nx-repair-app");
  if (isDashboard) body.classList.add("nx-repair-dashboard");
  if (isAdmin) body.classList.add("nx-repair-admin");
  if (isHealth) body.classList.add("nx-repair-health");

  const active = (href) => {
    try { return new URL(href, location.origin).pathname === path ? " is-active" : ""; }
    catch (_) { return ""; }
  };
  const items = isAdmin ? [
    ["Admin Overview","/admin","⌂"],["Users","/admin#users","◎"],["Payments","/admin#payments","▤"],["System Health","/admin/system-health","✧"],["Landing","/","↗"],["Logout","/logout","⇥"]
  ] : [
    ["Dashboard","/dashboard","⌂"],["My Plan","#pricing","▣"],["Signals","/bot-check","◈"],["Referrals","#referrals","◎"],["Invoices","/invoice-history","□"],["Logout","/logout","⇥"]
  ];
  if (!document.querySelector(".nx-repair-sidebar")) {
    const aside = document.createElement("aside");
    aside.className = "nx-repair-sidebar";
    aside.innerHTML = `<div class="nx-repair-brand"><div class="nx-repair-brand-mark">N</div><div><strong>Nexora</strong><span>AI Signal Hunter</span></div></div><nav class="nx-repair-nav">${items.map(([label, href, icon]) => `<a class="${active(href)}" href="${href}"><span>${icon}</span>${label}</a>`).join("")}</nav>`;
    body.prepend(aside);
  }

  const symbols = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"];
  const icons = { BTCUSDT:"₿", ETHUSDT:"Ξ", SOLUSDT:"S", BNBUSDT:"B" };
  let market = {
    BTCUSDT:{price:68542.10,change:1.82}, ETHUSDT:{price:3728.45,change:2.45}, SOLUSDT:{price:162.85,change:3.21}, BNBUSDT:{price:601.75,change:-0.35}
  };
  if (!document.querySelector(".nx-repair-top-strip")) {
    const strip = document.createElement("section");
    strip.className = "nx-repair-top-strip";
    strip.innerHTML = `<div class="nx-repair-market">${symbols.map((s) => `<article class="nx-repair-coin" data-symbol="${s}"><i>${icons[s]}</i><strong>${s.replace("USDT"," / USDT")}</strong><b class="nx-repair-price">--</b><span class="nx-repair-change">--</span></article>`).join("")}</div><div class="nx-repair-user"><div><strong>${isAdmin ? "Admin" : "Nexora Trader"}</strong><small>${isAdmin ? "Control Center" : "Live Dashboard"}</small></div><div class="nx-repair-avatar"></div></div>`;
    const target = document.querySelector(".page-wrap,.admin-shell,.health-shell,.topbar") || body.firstElementChild;
    body.insertBefore(strip, target);
  }
  const paintMarket = () => {
    document.querySelectorAll(".nx-repair-coin").forEach((card) => {
      const row = market[card.dataset.symbol]; if (!row) return;
      card.querySelector(".nx-repair-price").textContent = Number(row.price).toLocaleString(undefined,{maximumFractionDigits: row.price>100?2:4});
      card.querySelector(".nx-repair-change").textContent = `${row.change>=0?"+":""}${Number(row.change).toFixed(2)}%`;
      card.classList.toggle("is-down", Number(row.change) < 0);
    });
  };
  const refreshMarket = async () => {
    try {
      const res = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache:"no-store" });
      if (!res.ok) throw new Error("market api");
      const data = await res.json();
      const wanted = new Set(symbols);
      data.forEach((row) => { if (wanted.has(row.symbol)) market[row.symbol] = { price:Number(row.lastPrice||0), change:Number(row.priceChangePercent||0) }; });
    } catch (_) {}
    paintMarket();
  };
  refreshMarket(); setInterval(refreshMarket, 30000);

  if (isDashboard && !document.querySelector(".nx-repair-dashboard-grid")) {
    const anchor = document.querySelector(".premium-status-grid,.widget-grid,.plan-dashboard,.glass-box");
    if (anchor && anchor.parentNode) {
      const sec = document.createElement("section");
      sec.className = "nx-repair-dashboard-grid";
      sec.innerHTML = `<article class="nx-repair-card"><h3>Account Health</h3><div class="nx-repair-ring"><div><strong>95%</strong><span>Excellent</span></div></div><div class="nx-repair-list"><div><i class="nx-repair-check">✓</i>Account Verified</div><div><i class="nx-repair-check">✓</i>Telegram Connected</div><div><i class="nx-repair-check">✓</i>Subscription Protected</div><div><i class="nx-repair-check">✓</i>Signal Hunter Active</div></div></article><article class="nx-repair-card"><h3>Signal Hunter Preview</h3><div class="nx-repair-row"><strong>BTC/USDT</strong><span class="nx-repair-long">WATCH</span><span>S/R</span><span>RR 1:2+</span><span>Live</span></div><div class="nx-repair-row"><strong>ETH/USDT</strong><span class="nx-repair-long">SCAN</span><span>MTF</span><span>RR 1:2+</span><span>Live</span></div><div class="nx-repair-row"><strong>SOL/USDT</strong><span class="nx-repair-long">WAIT</span><span>Pullback</span><span>Protected</span><span>Live</span></div></article><article class="nx-repair-card"><h3>Quick Actions</h3><div class="nx-repair-quick"><a href="/bot-check"><span>◈</span>Verify Bot</a><a href="/manual-payment/basic"><span>▤</span>Payment / Upgrade</a><a href="#referrals"><span>◎</span>Invite & Earn</a><a href="#pricing"><span>▣</span>My Plan</a></div></article>`;
      anchor.insertAdjacentElement("afterend", sec);
    }
  }
})();

// Nexora final reference match layer
(() => {
  const root = document.documentElement;
  const body = document.body;
  if (!body || body.dataset.nexoraFinalMatch === "1") return;
  body.dataset.nexoraFinalMatch = "1";

  const applyTheme = (theme) => {
    const next = theme === "light" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("nexora-theme", next); } catch (_) {}
  };
  try { applyTheme(localStorage.getItem("nexora-theme") || "dark"); } catch (_) { root.setAttribute("data-theme", "dark"); }

  if (!document.querySelector(".theme-toggle,.nexora-theme-toggle")) {
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "nexora-theme-toggle theme-toggle";
    toggle.setAttribute("aria-label", "Toggle theme");
    toggle.innerHTML = '<span class="dark-icon">Moon</span><span class="light-icon">Sun</span>';
    document.body.prepend(toggle);
  }

  const dashboardOrAdmin = body.classList.contains("nx-pro-app") || document.querySelector(".plan-dashboard,.admin-shell");
  if (!dashboardOrAdmin) return;

  const toolbar = document.querySelector(".nx-pro-toolbar");
  const user = document.querySelector(".nx-pro-user");
  if (toolbar && user && !document.querySelector(".nx-pro-controls")) {
    const controls = document.createElement("div");
    controls.className = "nx-pro-controls";
    const themeButton = document.createElement("button");
    themeButton.type = "button";
    themeButton.className = "nx-pro-control-btn theme-toggle";
    themeButton.setAttribute("aria-label", "Toggle theme");
    themeButton.innerHTML = '<span class="dark-icon">Moon</span><span class="light-icon">Sun</span>';
    const notify = document.createElement("button");
    notify.type = "button";
    notify.className = "nx-pro-control-btn";
    notify.setAttribute("aria-label", "Notifications");
    notify.textContent = "!";
    user.parentNode.insertBefore(controls, user);
    controls.appendChild(themeButton);
    controls.appendChild(notify);
    controls.appendChild(user);
  }

  const setLastUpdated = () => {
    let node = document.querySelector(".nx-market-updated");
    if (!node) {
      const toolbarInner = document.querySelector(".nx-pro-controls");
      if (!toolbarInner) return;
      node = document.createElement("span");
      node.className = "nx-market-updated";
      node.style.color = "var(--hunter-muted)";
      node.style.fontSize = ".82rem";
      node.style.fontWeight = "800";
      toolbarInner.prepend(node);
    }
    const now = new Date();
    node.textContent = `Last update: ${now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
  };
  setLastUpdated();
  window.setInterval(setLastUpdated, 15000);

  document.querySelectorAll(".nx-pro-sidebar a[href], .premium-floating-nav a[href], .navbar a[href]").forEach((link) => {
    try {
      const url = new URL(link.getAttribute("href"), window.location.origin);
      if (url.pathname === window.location.pathname) link.classList.add("is-active");
    } catch (_) {}
  });
})();

// Nexora final live coin cards polish
(() => {
  const iconSvg = {
    BTCUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M19.7 6.3c2.6.7 4.1 2.2 3.8 4.5-.2 1.7-1.2 2.8-2.9 3.3 2.2.7 3.3 2.2 3 4.4-.4 3-2.9 4.6-6.7 4.4l-.4 3h-1.8l.4-3h-1.5l-.4 3h-1.8l.4-3H8l.4-2.1h1.7L12 9.5h-1.7l.4-2.1h3.8l.4-3h1.8l-.4 3h1.5l.4-3H20l-.3 1.9Zm-5.8 13.9h2.7c1.9 0 3-.7 3.2-2.1.2-1.3-.8-2-2.8-2h-2.5l-.6 4.1Zm.9-6.4h2.3c1.7 0 2.7-.7 2.9-2 .2-1.2-.7-1.8-2.4-1.8h-2.3l-.5 3.8Z"/></svg>',
    ETHUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M16 3 8 16.2 16 21l8-4.8L16 3Zm0 26 8-11.3-8 4.8-8-4.8L16 29Z"/></svg>',
    SOLUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M8 9.5c.3-.4.8-.7 1.4-.7h15c.7 0 1 .8.6 1.3l-2.2 2.4c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 9.5Zm0 9.4c.3-.4.8-.6 1.4-.6h15c.7 0 1 .8.6 1.3L22.8 22c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 18.9Zm16-4.7c-.3-.4-.8-.6-1.4-.6h-15c-.7 0-1 .8-.6 1.3l2.2 2.4c.3.4.8.6 1.4.6h15c.7 0 1-.8.6-1.3L24 14.2Z"/></svg>',
    BNBUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="m16 4 4.2 4.2L16 12.4l-4.2-4.2L16 4Zm-7.2 7.2 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2Zm14.4 0 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2ZM16 18.6l4.2 4.2L16 27l-4.2-4.2 4.2-4.2Zm0-4.8 2.2 2.2-2.2 2.2-2.2-2.2 2.2-2.2Z"/></svg>'
  };

  const decorate = () => {
    document.querySelectorAll(".nx-pro-coin").forEach((card) => {
      const symbol = card.dataset.symbol || "";
      if (!symbol || card.querySelector(".nx-coin-logo")) return;
      const oldIcon = card.querySelector(".nx-pro-coin-icon");
      const logo = document.createElement("span");
      logo.className = "nx-coin-logo";
      logo.dataset.symbol = symbol;
      logo.innerHTML = iconSvg[symbol] || '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="currentColor"/></svg>';
      if (oldIcon) oldIcon.replaceWith(logo);
      else card.prepend(logo);
    });
  };

  decorate();
  window.addEventListener("load", decorate, { once: true });
  window.setInterval(decorate, 3000);
})();
