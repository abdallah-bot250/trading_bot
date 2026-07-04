(() => {
  "use strict";
  const root = document.documentElement;
  const body = document.body;
  const storageKey = "nexora-theme";
  const path = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
  const isDashboard = path === "/dashboard" || path.startsWith("/dashboard/");
  const isAdmin = path === "/admin" || path.startsWith("/admin/");
  const isAuth = ["/login", "/register", "/forgot-password", "/reset-password"].some((p) => path === p || path.startsWith(p + "/"));
  const isLanding = path === "/";
  if (isDashboard) body.classList.add("nx-page-dashboard");
  if (isAdmin) body.classList.add("nx-page-admin");
  if (isAuth) body.classList.add("nx-page-auth");
  if (isLanding) body.classList.add("nx-page-landing");

  function getTheme(){try{return localStorage.getItem(storageKey)==="light"?"light":"dark"}catch(_){return"dark"}}
  function applyTheme(theme){
    const safe = theme === "light" ? "light" : "dark";
    root.setAttribute("data-theme", safe);
    try{localStorage.setItem(storageKey, safe)}catch(_){}
    document.querySelectorAll(".theme-toggle,.nx-theme-toggle,.nexora-theme-toggle").forEach((btn)=>{
      btn.setAttribute("aria-label", safe === "light" ? "Switch to dark mode" : "Switch to light mode");
      if(btn.classList.contains("nx-theme-toggle")) btn.textContent = safe === "light" ? "☀" : "◐";
    });
  }
  applyTheme(getTheme());
  document.addEventListener("click",(event)=>{
    const btn=event.target.closest(".theme-toggle,.nx-theme-toggle,.nexora-theme-toggle");
    if(!btn)return;
    event.preventDefault();
    applyTheme(root.getAttribute("data-theme")==="light"?"dark":"light");
  });
  function ensureThemeToggle(){
    if(document.querySelector(".theme-toggle,.nx-theme-toggle,.nexora-theme-toggle"))return;
    const btn=document.createElement("button");
    btn.type="button"; btn.className="nx-theme-toggle"; btn.textContent=root.getAttribute("data-theme")==="light"?"☀":"◐";
    btn.style.cssText="position:fixed;top:18px;inset-inline-end:18px;z-index:120;width:46px;height:46px;border-radius:14px;border:1px solid rgba(255,255,255,.16);background:rgba(5,12,20,.72);color:#fff;backdrop-filter:blur(16px);cursor:pointer";
    document.body.appendChild(btn);
  }
  ensureThemeToggle();

  function ensureDashboardReturn(){
    if(isDashboard || document.querySelector(".nx-dashboard-return"))return;
    const link=document.createElement("a");
    link.className="nx-dashboard-return";
    link.href="/dashboard";
    link.setAttribute("aria-label","Back to dashboard");
    link.innerHTML='<span>Dashboard</span>';
    document.body.appendChild(link);
  }
  ensureDashboardReturn();

  function cleanLegacyVisualLayers(){
    const selectors=[".nx-repair-sidebar",".nx-repair-top-strip",".nx-repair-dashboard-grid",".nx-pro-dashboard-grid",".nx-market-panel",".nx-health-strip",".nx-pro-market-strip",".nx-premium-sidebar",".nx-premium-topbar",".nx-legacy-marketbar",".nx-duplicate-marketbar",".nx-dashboard-sidebar",".nx-admin-sidebar"];
    document.querySelectorAll(selectors.join(",")).forEach((node)=>node.remove());
  }
  cleanLegacyVisualLayers();

  const dashboardLinks=[["Dashboard","/dashboard"],["My Plan","/my-plan"],["Signals","/signals"],["Auto Trading","/auto-trading"],["Referrals","/referrals"],["Payments","/payments"],["Invoices","/invoice-history"],["Profile","/profile"],["Settings","/settings"],["Logout","/logout"]];
  const adminLinks=[["Admin Overview","/admin"],["Users","/admin/users"],["Subscriptions","/admin/subscriptions"],["Payments","/admin/payments"],["Manual Payments","/admin/manual-payments"],["Repair Pro 2Y","/admin/repair-pro-2y"],["System Health","/admin/system-health"],["Settings","/admin/settings"],["Logout","/logout"]];

  function buildSidebar(kind){
    if(!(isDashboard||isAdmin))return;
    if(document.querySelector(".nx-final-sidebar"))return;
    body.classList.add("nx-has-sidebar");
    const sidebar=document.createElement("aside"); sidebar.className="nx-final-sidebar";
    const links=kind==="admin"?adminLinks:dashboardLinks;
    sidebar.innerHTML=`<div class="nx-final-brand"><strong>NEXORA</strong><span>${kind==="admin"?"CONTROL CENTER":"TRADING CONSOLE"}</span></div><nav class="nx-final-nav">${links.map(([label,href],i)=>`<a href="${href}" class="${i===0?"active":""}">${label}</a>`).join("")}</nav><div class="nx-sidebar-note"><strong>${kind==="admin"?"Admin Tools":"Account Console"}</strong><br>${kind==="admin"?"Monitor users, payments and system status.":"Track subscription, Telegram and signal status."}</div>`;
    document.body.prepend(sidebar);
  }
  buildSidebar(isAdmin?"admin":"dashboard");

  function addAdminAnchors(){
    if(!isAdmin)return;
    const map={"user":"users","subscription":"subscriptions","payment":"payments","manual payment":"manual-payments","repair pro 2y":"repair-pro-2y","coupon":"settings","system status":"overview","affiliate":"overview","ai performance":"overview","growth":"subscriptions"};
    document.querySelectorAll("h2,h3,.label,.section-title h2").forEach((el)=>{
      const txt=(el.textContent||"").trim().toLowerCase();
      Object.keys(map).forEach((key)=>{ if(txt.includes(key)){ const section=el.closest("section,.section,.ops-panel,.overview-card,.hero-main")||el; if(!section.id)section.id=map[key]; }});
    });
    const first=document.querySelector(".admin-shell,.hero,.hero-main"); if(first&&!first.id) first.id="overview";
    document.querySelectorAll('.nx-final-nav a[href*="#"]').forEach((a)=>{
      a.addEventListener('click',()=>{document.querySelectorAll('.nx-final-nav a').forEach(x=>x.classList.remove('active'));a.classList.add('active')});
    });
  }
  addAdminAnchors();

  const marketFallback={BTCUSDT:{label:"BTC/USDT",icon:"BTC",cls:"btc",price:"60,023.52",change:"-0.19"},ETHUSDT:{label:"ETH/USDT",icon:"ETH",cls:"eth",price:"1,579.37",change:"+0.47"},SOLUSDT:{label:"SOL/USDT",icon:"SOL",cls:"sol",price:"72.23",change:"+2.05"},BNBUSDT:{label:"BNB/USDT",icon:"BNB",cls:"bnb",price:"553.41",change:"-0.43"},XRPUSDT:{label:"XRP/USDT",icon:"XRP",cls:"xrp",price:"0.5284",change:"+1.02"},ADAUSDT:{label:"ADA/USDT",icon:"ADA",cls:"ada",price:"0.3987",change:"+0.71"},DOGEUSDT:{label:"DOGE/USDT",icon:"DOGE",cls:"doge",price:"0.1152",change:"-0.65"}};
  const symbols=Object.keys(marketFallback); const cache=new Map();
  function formatPrice(value){const n=Number(value);if(!Number.isFinite(n))return value||"--";return n>=1000?n.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}):n.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:4})}
  function renderMarketBar(){
    if(!(isDashboard||isAdmin))return; if(document.querySelector(".nx-final-marketbar"))return;
    const bar=document.createElement("section"); bar.className="nx-final-marketbar"; bar.setAttribute("aria-label","Live crypto market prices");
    bar.innerHTML=symbols.map((symbol)=>{const item=marketFallback[symbol];return `<article class="nx-market-card" data-nx-symbol="${symbol}"><div class="nx-market-left"><span class="nx-coin ${item.cls}">${item.icon}</span><span class="nx-symbol">${item.label}</span></div><strong class="nx-price">${item.price}</strong><span class="nx-change ${String(item.change).startsWith("-")?"down":""}">${item.change}%</span></article>`}).join("")+`<div class="nx-market-meta"><span>LIVE</span><span class="nx-dot"></span><small>Market Open</small></div>`;
    document.body.insertBefore(bar, document.body.firstChild.nextSibling);
  }
  function applyMarketValues(values){symbols.forEach((symbol)=>{const node=document.querySelector(`[data-nx-symbol="${symbol}"]`);if(!node)return;const fallback=marketFallback[symbol];const item=values[symbol]||cache.get(symbol)||fallback;const price=node.querySelector(".nx-price");const change=node.querySelector(".nx-change");if(price)price.textContent=formatPrice(item.price||item.lastPrice||fallback.price);if(change){const ch=Number(item.change??item.priceChangePercent??fallback.change);const txt=Number.isFinite(ch)?`${ch>=0?"+":""}${ch.toFixed(2)}%`:`${fallback.change}%`;change.textContent=txt;change.classList.toggle("down",txt.startsWith("-"));}})}
  async function refreshMarket(){if(!(isDashboard||isAdmin))return;const fallbackValues={};symbols.forEach(s=>fallbackValues[s]=cache.get(s)||marketFallback[s]);try{const url=`https://api.binance.us/api/v3/ticker/24hr?symbols=${encodeURIComponent(JSON.stringify(symbols))}`;const response=await fetch(url,{cache:"no-store"});if(!response.ok)throw new Error("market api failed");const data=await response.json();const values={};data.forEach((row)=>{if(!row||!row.symbol||!symbols.includes(row.symbol))return;values[row.symbol]={price:row.lastPrice,change:row.priceChangePercent};cache.set(row.symbol,values[row.symbol]);});applyMarketValues(values)}catch(_){applyMarketValues(fallbackValues)}}
  renderMarketBar(); refreshMarket(); if(isDashboard||isAdmin)window.setInterval(refreshMarket,15000);
})();
