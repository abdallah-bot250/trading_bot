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
