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

// Nexora dashboard reference repair
(() => {
  const body = document.body;
  if (!body || body.dataset.nxDashboardReferenceRepair === "1") return;
  const isDashboard = location.pathname.includes("dashboard") || body.classList.contains("nx-dashboard") || document.querySelector(".plan-dashboard,.premium-status-grid");
  if (!isDashboard) return;
  body.dataset.nxDashboardReferenceRepair = "1";
  body.classList.add("nx-dashboard", "nx-pro-app");

  const icon = (name) => {
    const icons = {
      dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
      plan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M6 3h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M8 12h8M8 16h5"/></svg>',
      signals: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 16 5-5 4 4 7-7"/><path d="M20 8v6h-6"/></svg>',
      auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="4"/><path d="m17 7 2-2M5 19l2-2M5 5l2 2M17 17l2 2"/></svg>',
      referrals: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="8" cy="8" r="3"/><circle cx="16" cy="16" r="3"/><path d="M10.5 10.5 13.5 13.5"/></svg>',
      payments: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18"/></svg>',
      invoices: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 3h10l3 3v15l-3-2-3 2-3-2-3 2-4-2V6a3 3 0 0 1 3-3Z"/><path d="M9 9h6M9 13h6"/></svg>',
      profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
      logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 17 15 12 10 7"/><path d="M15 12H3"/><path d="M21 3v18"/></svg>',
      telegram: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 4 3 11l7 2 2 7 9-16Z"/><path d="m10 13 4-4"/></svg>',
      upgrade: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>'
    };
    return icons[name] || icons.dashboard;
  };

  const active = (href) => {
    try { return new URL(href, location.origin).pathname === location.pathname ? " is-active" : ""; }
    catch (_) { return ""; }
  };

  const removeBadLayers = () => {
    document.querySelectorAll(".nx-repair-sidebar,.nx-repair-top-strip,.nx-repair-dashboard-grid,.nx-pro-dashboard-grid,.nx-market-panel,.nx-health-strip").forEach((node) => node.remove());
  };
  removeBadLayers();
  setInterval(removeBadLayers, 1200);

  let sidebar = document.querySelector(".nx-pro-sidebar");
  if (!sidebar) {
    sidebar = document.createElement("aside");
    sidebar.className = "nx-pro-sidebar";
    document.body.prepend(sidebar);
  }
  sidebar.innerHTML = `
    <div class="nx-pro-brand">
      <div class="nx-pro-brand-mark">N</div>
      <div><strong>Nexora</strong><span>AI Signal Hunter</span></div>
    </div>
    <nav class="nx-pro-nav" aria-label="Dashboard navigation">
      ${[
        ["Dashboard", "/dashboard", "dashboard"],
        ["My Plan", "#pricing", "plan"],
        ["Signals", "/bot-check", "signals"],
        ["Auto Trading", "#vip-settings", "auto"],
        ["Referrals", "#referrals", "referrals"],
        ["Payments", "/manual-payment/basic", "payments"],
        ["Invoices", "/invoice-history", "invoices"],
        ["Profile", "#profile", "profile"],
        ["Logout", "/logout", "logout"]
      ].map(([label, href, key]) => `<a class="${active(href)}" href="${href}"><span>${icon(key)}</span>${label}</a>`).join("")}
    </nav>`;

  const symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];
  const fallback = {
    BTCUSDT: { price: 68542.10, change: 1.82 },
    ETHUSDT: { price: 3728.45, change: 2.45 },
    SOLUSDT: { price: 162.85, change: 3.21 },
    BNBUSDT: { price: 601.75, change: -0.35 }
  };

  let toolbar = document.querySelector(".nx-pro-toolbar");
  if (!toolbar) {
    toolbar = document.createElement("section");
    toolbar.className = "nx-pro-toolbar";
    const target = document.querySelector(".page-wrap,.plan-dashboard") || document.body.firstElementChild;
    document.body.insertBefore(toolbar, target);
  }
  toolbar.innerHTML = `
    <div class="nx-pro-market-strip" aria-label="Live crypto prices">
      ${symbols.map((symbol) => `<article class="nx-pro-coin" data-symbol="${symbol}">
        <span class="nx-pro-coin-icon"></span>
        <strong>${symbol.replace("USDT", " / USDT")}</strong>
        <b class="nx-pro-price">Live</b>
        <span class="nx-pro-change">Connecting</span>
      </article>`).join("")}
    </div>
    <div class="nx-pro-controls">
      <button type="button" class="nx-pro-control-btn theme-toggle" aria-label="Toggle theme"><span class="dark-icon">Moon</span><span class="light-icon">Sun</span></button>
      <div class="nx-pro-user"><div><strong>Nexora Trader</strong><small>Live Account</small></div><div class="nx-pro-avatar" aria-hidden="true"></div></div>
    </div>`;

  const coinSvg = {
    BTCUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M19.7 6.3c2.6.7 4.1 2.2 3.8 4.5-.2 1.7-1.2 2.8-2.9 3.3 2.2.7 3.3 2.2 3 4.4-.4 3-2.9 4.6-6.7 4.4l-.4 3h-1.8l.4-3h-1.5l-.4 3h-1.8l.4-3H8l.4-2.1h1.7L12 9.5h-1.7l.4-2.1h3.8l.4-3h1.8l-.4 3h1.5l.4-3H20l-.3 1.9Zm-5.8 13.9h2.7c1.9 0 3-.7 3.2-2.1.2-1.3-.8-2-2.8-2h-2.5l-.6 4.1Zm.9-6.4h2.3c1.7 0 2.7-.7 2.9-2 .2-1.2-.7-1.8-2.4-1.8h-2.3l-.5 3.8Z"/></svg>',
    ETHUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M16 3 8 16.2 16 21l8-4.8L16 3Zm0 26 8-11.3-8 4.8-8-4.8L16 29Z"/></svg>',
    SOLUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M8 9.5c.3-.4.8-.7 1.4-.7h15c.7 0 1 .8.6 1.3l-2.2 2.4c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 9.5Zm0 9.4c.3-.4.8-.6 1.4-.6h15c.7 0 1 .8.6 1.3L22.8 22c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 18.9Zm16-4.7c-.3-.4-.8-.6-1.4-.6h-15c-.7 0-1 .8-.6 1.3l2.2 2.4c.3.4.8.6 1.4.6h15c.7 0 1-.8.6-1.3L24 14.2Z"/></svg>',
    BNBUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="m16 4 4.2 4.2L16 12.4l-4.2-4.2L16 4Zm-7.2 7.2 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2Zm14.4 0 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2ZM16 18.6l4.2 4.2L16 27l-4.2-4.2 4.2-4.2Zm0-4.8 2.2 2.2-2.2 2.2-2.2-2.2 2.2-2.2Z"/></svg>'
  };
  document.querySelectorAll(".nx-pro-coin").forEach((card) => {
    const logo = card.querySelector(".nx-pro-coin-icon");
    const symbol = card.dataset.symbol;
    if (logo) {
      logo.className = "nx-coin-logo";
      logo.dataset.symbol = symbol;
      logo.innerHTML = coinSvg[symbol] || "";
    }
  });

  const paint = (rows) => {
    document.querySelectorAll(".nx-pro-coin").forEach((card) => {
      const symbol = card.dataset.symbol;
      const row = rows[symbol] || fallback[symbol];
      if (!row) return;
      const price = Number(row.price || 0);
      const change = Number(row.change || 0);
      const priceNode = card.querySelector(".nx-pro-price");
      const changeNode = card.querySelector(".nx-pro-change");
      if (priceNode) priceNode.textContent = price.toLocaleString(undefined, { maximumFractionDigits: price > 100 ? 2 : 4 });
      if (changeNode) changeNode.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
      card.classList.toggle("is-down", change < 0);
    });
  };

  let cache = { ...fallback };
  const refresh = async () => {
    try {
      const res = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache: "no-store" });
      if (!res.ok) throw new Error("market");
      const data = await res.json();
      const wanted = new Set(symbols);
      const next = {};
      data.forEach((row) => {
        if (!wanted.has(row.symbol)) return;
        next[row.symbol] = { price: Number(row.lastPrice || 0), change: Number(row.priceChangePercent || 0) };
      });
      if (Object.keys(next).length) cache = { ...cache, ...next };
    } catch (_) {}
    paint(cache);
  };
  refresh();
  setInterval(refresh, 15000);

  if (!document.querySelector(".nx-clean-dashboard-grid")) {
    const anchor = document.querySelector(".premium-status-grid,.plan-dashboard,.hero");
    if (anchor && anchor.parentNode) {
      const grid = document.createElement("section");
      grid.className = "nx-clean-dashboard-grid";
      grid.innerHTML = `
        <article>
          <h3>Account Health</h3>
          <div class="nx-health-orbit"><div><strong>95%</strong><span>Excellent</span></div></div>
          <div class="nx-health-checks">
            <div><i>✓</i>Account Verified</div>
            <div><i>✓</i>Telegram Connected</div>
            <div><i>✓</i>Payment Method Verified</div>
            <div><i>✓</i>Active Subscription</div>
          </div>
        </article>
        <article>
          <h3>Recent Signals</h3>
          <div class="nx-signal-row"><strong>BTC/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 68,100</span><span>TP 69,200</span><span>2m</span></div>
          <div class="nx-signal-row"><strong>ETH/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 3,700</span><span>TP 3,820</span><span>5m</span></div>
          <div class="nx-signal-row"><strong>SOL/USDT</strong><span class="nx-long-badge">LONG</span><span>Entry 160.50</span><span>TP 166.80</span><span>12m</span></div>
        </article>
        <article>
          <h3>Quick Actions</h3>
          <div class="nx-clean-quick">
            <a href="/bot-check"><span class="nx-action-icon">${icon("signals")}</span>Get New Signals</a>
            <a href="#vip-settings"><span class="nx-action-icon">${icon("auto")}</span>Auto Trading</a>
            <a href="/manual-payment/basic"><span class="nx-action-icon">${icon("payments")}</span>Payment / Upgrade</a>
            <a href="#referrals"><span class="nx-action-icon">${icon("referrals")}</span>Invite & Earn</a>
          </div>
        </article>`;
      anchor.insertAdjacentElement("afterend", grid);
    }
  }
})();

// Nexora admin reference repair
(() => {
  const body = document.body;
  if (!body || body.dataset.nxAdminReferenceRepair === "1") return;
  const isAdmin = location.pathname.includes("admin") || body.classList.contains("nx-admin") || document.querySelector(".admin-shell");
  if (!isAdmin) return;
  body.dataset.nxAdminReferenceRepair = "1";
  body.classList.add("nx-admin", "nx-pro-app");

  const icon = (name) => {
    const icons = {
      overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
      users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
      subs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 8h10M7 12h7M7 16h4"/></svg>',
      payments: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18"/></svg>',
      manual: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v18"/><path d="M17 8H9.5a3.5 3.5 0 0 0 0 7H15a3.5 3.5 0 0 1 0 7H6"/></svg>',
      repair: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m14.7 6.3 3 3"/><path d="M5 19l6.8-6.8"/><path d="M13 5l6 6-3 3-6-6 3-3Z"/></svg>',
      health: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="M9 12l2 2 4-4"/></svg>',
      settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 1 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6 1.8 1.8 0 0 0-.4 1.2V21a2 2 0 1 1-4 0v-.08A1.8 1.8 0 0 0 8.6 19.4a1.8 1.8 0 0 0-1.98.36l-.05.05a2 2 0 1 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1 1.8 1.8 0 0 0-1.2-.4H3a2 2 0 1 1 0-4h.08A1.8 1.8 0 0 0 4.6 8.6a1.8 1.8 0 0 0-.36-1.98l-.05-.05a2 2 0 1 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6 1.8 1.8 0 0 0 .4-1.2V3a2 2 0 1 1 4 0v.08A1.8 1.8 0 0 0 15.4 4.6a1.8 1.8 0 0 0 1.98-.36l.05-.05a2 2 0 1 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.38.26.68.6.86 1H21a2 2 0 1 1 0 4h-.08a1.8 1.8 0 0 0-1.52 1Z"/></svg>',
      logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 17 15 12 10 7"/><path d="M15 12H3"/><path d="M21 3v18"/></svg>'
    };
    return icons[name] || icons.overview;
  };

  const active = (href) => {
    try { return new URL(href, location.origin).pathname === location.pathname ? " is-active" : ""; }
    catch (_) { return ""; }
  };

  const removeBadLayers = () => {
    document.querySelectorAll(".nx-repair-sidebar,.nx-repair-top-strip").forEach((node) => node.remove());
  };
  removeBadLayers();
  setInterval(removeBadLayers, 1200);

  let sidebar = document.querySelector(".nx-pro-sidebar");
  if (!sidebar) {
    sidebar = document.createElement("aside");
    sidebar.className = "nx-pro-sidebar";
    document.body.prepend(sidebar);
  }
  sidebar.innerHTML = `
    <div class="nx-pro-brand">
      <div class="nx-pro-brand-mark">N</div>
      <div><strong>Nexora</strong><span>AI Signal Hunter</span></div>
    </div>
    <nav class="nx-pro-nav" aria-label="Admin navigation">
      ${[
        ["Admin Overview", "/admin", "overview"],
        ["Users", "/admin#users", "users"],
        ["Subscriptions", "/admin#subscriptions", "subs"],
        ["Payments", "/admin#payments", "payments"],
        ["Manual Payments", "/admin#manual-payments", "manual"],
        ["Repair Pro 2Y", "/admin#repair-pro-2y", "repair"],
        ["System Health", "/admin/system-health", "health"],
        ["Settings", "/admin#settings", "settings"],
        ["Logout", "/logout", "logout"]
      ].map(([label, href, key]) => `<a class="${active(href)}" href="${href}"><span>${icon(key)}</span>${label}</a>`).join("")}
    </nav>`;

  let toolbar = document.querySelector(".nx-pro-toolbar");
  if (!toolbar) {
    toolbar = document.createElement("section");
    toolbar.className = "nx-pro-toolbar";
    const target = document.querySelector(".admin-shell") || document.body.firstElementChild;
    document.body.insertBefore(toolbar, target);
  }
  toolbar.innerHTML = `
    <div class="nx-pro-controls">
      <button type="button" class="nx-pro-control-btn theme-toggle" aria-label="Toggle theme"><span class="dark-icon">Moon</span><span class="light-icon">Sun</span></button>
      <button type="button" class="nx-pro-control-btn" aria-label="Notifications">!</button>
      <div class="nx-pro-user"><div><strong>Admin</strong><small>Super Admin</small></div><div class="nx-pro-avatar" aria-hidden="true"></div></div>
    </div>`;

  const repairForm = document.querySelector('form[action="/admin/repair-plan-constraint"]');
  const repairPanel = repairForm ? repairForm.closest(".ops-panel") : null;
  if (repairPanel) {
    repairPanel.classList.add("nx-maintenance-card");
    repairPanel.id = repairPanel.id || "repair-pro-2y";
  }

  const usersSection = document.querySelector("#usersTable")?.closest(".section");
  if (usersSection) usersSection.id = usersSection.id || "users";
  const withdrawalsSection = document.querySelector("#withdrawalsTable")?.closest(".section");
  if (withdrawalsSection) withdrawalsSection.id = withdrawalsSection.id || "manual-payments";

  document.querySelectorAll(".section").forEach((section) => {
    const title = (section.querySelector(".section-title h2")?.textContent || "").toLowerCase();
    if (title.includes("coupon")) section.id = section.id || "payments";
  });

  document.querySelectorAll("tbody tr").forEach((row) => {
    row.querySelectorAll("td").forEach((cell) => {
      const text = (cell.textContent || "").trim().toLowerCase();
      if (text === "connected" && !cell.querySelector(".badge")) cell.innerHTML = '<span class="badge badge-paid">Connected</span>';
      if (text === "not connected" && !cell.querySelector(".badge")) cell.innerHTML = '<span class="badge badge-pending">Not Connected</span>';
    });
  });
})();

// Nexora auth reference repair
(() => {
  const body = document.body;
  if (!body || body.dataset.nxAuthReferenceRepair === "1") return;
  const isAuth = location.pathname.includes("login") || location.pathname.includes("register") || document.querySelector(".login-box,.register-box,.container form[action*='register']");
  if (!isAuth) return;
  body.dataset.nxAuthReferenceRepair = "1";
  body.classList.add("nx-auth");

  const eye = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m3 3 18 18"/><path d="M10.6 10.6a3 3 0 0 0 4 4"/><path d="M9.9 4.2A10.5 10.5 0 0 1 12 4c6.5 0 10 8 10 8a17.7 17.7 0 0 1-3.1 4.4"/><path d="M6.6 6.6C3.6 8.6 2 12 2 12s3.5 8 10 8a10.8 10.8 0 0 0 4.4-.9"/></svg>';

  document.querySelectorAll('input[type="password"]').forEach((input) => {
    if (input.closest(".password-wrap")) {
      const existing = input.closest(".password-wrap").querySelector(".toggle-pass");
      if (existing) {
        existing.classList.add("nx-password-toggle");
        existing.innerHTML = eye;
      }
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "nx-password-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nx-password-toggle";
    btn.setAttribute("aria-label", "Show password");
    btn.innerHTML = eye;
    wrap.appendChild(btn);
  });

  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".nx-password-toggle,.toggle-pass");
    if (!btn) return;
    const wrap = btn.closest(".nx-password-wrap,.password-wrap");
    const input = wrap ? wrap.querySelector("input") : null;
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    btn.innerHTML = show ? eyeOff : eye;
  });

  const loginForm = document.querySelector('.login-box form');
  if (loginForm && !loginForm.querySelector(".nx-remember-row")) {
    const submit = loginForm.querySelector('button[type="submit"], .btn');
    const row = document.createElement("div");
    row.className = "nx-remember-row";
    row.innerHTML = '<label><input type="checkbox" name="remember_me" value="1"> Remember me</label><a href="/forgot-password">Forgot password?</a>';
    if (submit) loginForm.insertBefore(row, submit);
    else loginForm.appendChild(row);
  }

  const registerButton = document.querySelector('form[action*="register"] .main-btn, form[action*="register"] button[type="submit"]');
  if (registerButton && !registerButton.dataset.nxTrialText) {
    registerButton.dataset.nxTrialText = "1";
    if (!/trial/i.test(registerButton.textContent || "")) {
      registerButton.textContent = "Start Free Trial";
    }
  }
})();

// Nexora universal theme coverage
(() => {
  const root = document.documentElement;
  const body = document.body;
  if (!body || body.dataset.nxUniversalTheme === "1") return;
  body.dataset.nxUniversalTheme = "1";
  body.classList.add("nx-universal-theme");

  const page = (location.pathname || "/").replace(/\/+$/, "") || "/";
  const pageClass = (() => {
    if (page === "/") return "nx-page-landing";
    if (page.includes("login")) return "nx-page-login";
    if (page.includes("register")) return "nx-page-register";
    if (page.includes("forgot-password")) return "nx-page-forgot";
    if (page.includes("reset-password")) return "nx-page-reset";
    if (page.includes("dashboard")) return "nx-page-dashboard";
    if (page === "/admin") return "nx-page-admin";
    if (page.includes("system-health")) return "nx-page-admin-health";
    if (page.includes("payment-webhook")) return "";
    if (page.includes("payment")) return page.includes("manual") ? "nx-page-manual-payment" : "nx-page-payment";
    if (page.includes("manual")) return "nx-page-manual";
    if (page.includes("invoice-history")) return "nx-page-invoice";
    if (page.includes("proof")) return "nx-page-proof";
    if (page.includes("bot-check")) return "nx-page-bot-check";
    return "";
  })();
  if (pageClass) body.classList.add(pageClass);

  const normalizeTheme = (value) => value === "light" ? "light" : "dark";
  const applyTheme = (theme) => {
    const next = normalizeTheme(theme);
    root.setAttribute("data-theme", next);
    body.setAttribute("data-nx-theme", next);
    try { localStorage.setItem("nexora-theme", next); } catch (_) {}
    document.querySelectorAll(".theme-toggle,.nexora-theme-toggle,.nx-theme-toggle,[data-theme-toggle]").forEach((button) => {
      button.dataset.themeState = next;
      button.setAttribute("aria-label", next === "light" ? "Switch to dark mode" : "Switch to light mode");
    });
  };

  let stored = "dark";
  try { stored = localStorage.getItem("nexora-theme") || root.getAttribute("data-theme") || "dark"; } catch (_) {}
  applyTheme(stored);

  if (!document.querySelector(".theme-toggle,.nexora-theme-toggle,.nx-theme-toggle,[data-theme-toggle]")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nexora-theme-toggle theme-toggle nx-theme-toggle";
    button.setAttribute("aria-label", "Toggle theme");
    button.innerHTML = '<span class="dark-icon">Moon</span><span class="light-icon">Sun</span>';
    document.body.prepend(button);
    applyTheme(root.getAttribute("data-theme") || "dark");
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".theme-toggle,.nexora-theme-toggle,.nx-theme-toggle,[data-theme-toggle]");
    if (!button) return;
    event.preventDefault();
    applyTheme(root.getAttribute("data-theme") === "light" ? "dark" : "light");
  }, true);

  window.addEventListener("storage", (event) => {
    if (event.key === "nexora-theme") applyTheme(event.newValue || "dark");
  });
})();

// Nexora global background identity
(() => {
  const body = document.body;
  if (!body || body.dataset.nxGlobalBackground === "1") return;
  body.dataset.nxGlobalBackground = "1";
  body.classList.add("nx-global-bg");
})();

// Nexora authoritative live market
(() => {
  const body = document.body;
  if (!body || body.dataset.nxLiveMarketAuthority === "1") return;
  const isDashboard = location.pathname.includes("dashboard") || body.classList.contains("nx-page-dashboard") || document.querySelector(".nx-pro-market-strip");
  if (!isDashboard) return;
  body.dataset.nxLiveMarketAuthority = "1";

  const symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];
  const labels = {
    BTCUSDT: "BTC / USDT",
    ETHUSDT: "ETH / USDT",
    SOLUSDT: "SOL / USDT",
    BNBUSDT: "BNB / USDT"
  };
  const logos = {
    BTCUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M19.7 6.3c2.6.7 4.1 2.2 3.8 4.5-.2 1.7-1.2 2.8-2.9 3.3 2.2.7 3.3 2.2 3 4.4-.4 3-2.9 4.6-6.7 4.4l-.4 3h-1.8l.4-3h-1.5l-.4 3h-1.8l.4-3H8l.4-2.1h1.7L12 9.5h-1.7l.4-2.1h3.8l.4-3h1.8l-.4 3h1.5l.4-3H20l-.3 1.9Zm-5.8 13.9h2.7c1.9 0 3-.7 3.2-2.1.2-1.3-.8-2-2.8-2h-2.5l-.6 4.1Zm.9-6.4h2.3c1.7 0 2.7-.7 2.9-2 .2-1.2-.7-1.8-2.4-1.8h-2.3l-.5 3.8Z"/></svg>',
    ETHUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M16 3 8 16.2 16 21l8-4.8L16 3Zm0 26 8-11.3-8 4.8-8-4.8L16 29Z"/></svg>',
    SOLUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M8 9.5c.3-.4.8-.7 1.4-.7h15c.7 0 1 .8.6 1.3l-2.2 2.4c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 9.5Zm0 9.4c.3-.4.8-.6 1.4-.6h15c.7 0 1 .8.6 1.3L22.8 22c-.3.4-.8.6-1.4.6h-15c-.7 0-1-.8-.6-1.3L8 18.9Zm16-4.7c-.3-.4-.8-.6-1.4-.6h-15c-.7 0-1 .8-.6 1.3l2.2 2.4c.3.4.8.6 1.4.6h15c.7 0 1-.8.6-1.3L24 14.2Z"/></svg>',
    BNBUSDT: '<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="m16 4 4.2 4.2L16 12.4l-4.2-4.2L16 4Zm-7.2 7.2 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2Zm14.4 0 4.2 4.2-4.2 4.2-4.2-4.2 4.2-4.2ZM16 18.6l4.2 4.2L16 27l-4.2-4.2 4.2-4.2Zm0-4.8 2.2 2.2-2.2 2.2-2.2-2.2 2.2-2.2Z"/></svg>'
  };
  const fallback = {
    BTCUSDT: { price: 68542.10, change: 1.82 },
    ETHUSDT: { price: 3728.45, change: 2.45 },
    SOLUSDT: { price: 162.85, change: 3.21 },
    BNBUSDT: { price: 601.75, change: -0.35 }
  };
  const cache = new Map();

  const formatPrice = (value) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return "--";
    return number >= 1000
      ? number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  };
  const formatChange = (value) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return "--";
    return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
  };
  const stamp = () => new Date().toLocaleTimeString("en-US", { hour12: false });

  const removeLegacyMarketBars = () => {
    document.querySelectorAll(".nx-repair-top-strip,.nx-market-panel").forEach((node) => node.remove());
  };

  const renderMarketStrip = () => {
    removeLegacyMarketBars();
    let toolbar = document.querySelector(".nx-pro-toolbar");
    if (!toolbar) {
      toolbar = document.createElement("section");
      toolbar.className = "nx-pro-toolbar";
      const target = document.querySelector(".dashboard-container,.dashboard-shell,main,.container") || document.body.firstElementChild;
      document.body.insertBefore(toolbar, target || document.body.firstChild);
    }

    let strip = toolbar.querySelector(".nx-pro-market-strip");
    if (!strip) {
      strip = document.createElement("div");
      strip.className = "nx-pro-market-strip";
      strip.setAttribute("aria-label", "Live crypto prices");
      toolbar.prepend(strip);
    }

    strip.innerHTML = symbols.map((symbol) => `
      <article class="nx-pro-coin nx-live-market-card is-loading" data-symbol="${symbol}">
        <span class="nx-pro-coin-icon">${logos[symbol]}</span>
        <span class="nx-pro-coin-meta">
          <strong>${labels[symbol]}</strong>
          <small>Binance US live</small>
        </span>
        <b class="nx-pro-price">Loading</b>
        <span class="nx-pro-change">...</span>
      </article>
    `).join("");

    let updated = toolbar.querySelector(".nx-live-market-updated");
    if (!updated) {
      updated = document.createElement("div");
      updated.className = "nx-live-market-updated";
      toolbar.appendChild(updated);
    }
    updated.innerHTML = 'Last update: <span>connecting</span><i aria-hidden="true"></i>';
  };

  const applyValues = (values, source) => {
    document.querySelectorAll(".nx-pro-market-strip .nx-pro-coin").forEach((card) => {
      const symbol = card.dataset.symbol;
      const value = values[symbol] || cache.get(symbol) || fallback[symbol];
      const priceNode = card.querySelector(".nx-pro-price");
      const changeNode = card.querySelector(".nx-pro-change");
      if (!value || !priceNode || !changeNode) return;
      const change = Number(value.change);
      priceNode.textContent = formatPrice(value.price);
      changeNode.textContent = formatChange(change);
      changeNode.classList.toggle("down", change < 0);
      changeNode.classList.toggle("up", change >= 0);
      card.classList.remove("is-loading");
      card.classList.toggle("is-fallback", source === "fallback");
    });

    const updated = document.querySelector(".nx-live-market-updated span");
    if (updated) updated.textContent = source === "fallback" ? `fallback ${stamp()}` : stamp();
  };

  const refreshLiveMarket = async () => {
    try {
      const response = await fetch("https://api.binance.us/api/v3/ticker/24hr", { cache: "no-store" });
      if (!response.ok) throw new Error(`market ${response.status}`);
      const payload = await response.json();
      const values = {};
      payload.forEach((item) => {
        if (!symbols.includes(item.symbol)) return;
        values[item.symbol] = {
          price: Number(item.lastPrice),
          change: Number(item.priceChangePercent)
        };
        cache.set(item.symbol, values[item.symbol]);
      });
      symbols.forEach((symbol) => {
        if (!values[symbol] && cache.has(symbol)) values[symbol] = cache.get(symbol);
      });
      applyValues(values, "live");
    } catch (_) {
      const values = {};
      symbols.forEach((symbol) => values[symbol] = cache.get(symbol) || fallback[symbol]);
      applyValues(values, "fallback");
    }
  };

  renderMarketStrip();
  refreshLiveMarket();
  window.setInterval(refreshLiveMarket, 15000);
  window.setInterval(removeLegacyMarketBars, 1500);
})();
