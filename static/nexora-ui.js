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
