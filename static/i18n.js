(() => {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("nexora-theme");
  root.setAttribute("data-theme", savedTheme || "dark");

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".theme-toggle");
    if (!button) return;
    const current = root.getAttribute("data-theme") || "dark";
    const next = current === "light" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem("nexora-theme", next);
  });

  const lang = window.NEXORA_LANG || document.documentElement.lang || "en";
  const pairs = [
    ["الرئيسية", "Home"],
    ["الإثباتات", "Proof"],
    ["تجارب المستخدمين", "User Proof"],
    ["فحص البوت", "Bot Check"],
    ["تأكد من البوت", "Verify Bot"],
    ["الداشبورد", "Dashboard"],
    ["لوحة التحكم", "Dashboard"],
    ["دخول", "Login"],
    ["تسجيل الدخول", "Login"],
    ["إنشاء حساب", "Create Account"],
    ["ابدأ الآن", "Get Started"],
    ["ابدأ التجربة", "Start Trial"],
    ["شاهد الديمو", "View Demo"],
    ["شاهد النتائج", "View Results"],
    ["منصة إشارات كريبتو ذكية للمتداول الجاد", "AI crypto signal platform for serious traders"],
    ["إشارات منتقاة", "Curated Signals"],
    ["لوحة تحكم كاملة", "Complete Dashboard"],
    ["ربط تيليجرام", "Telegram Linking"],
    ["دفع يدوي وأوتوماتيك", "Manual and Automatic Payments"],
    ["تجربة مجانية", "Free Trial"],
    ["كيف يفكر النظام؟", "How the system thinks"],
    ["اختبر النظام", "Try the System"],
    ["خطط واضحة بدون تعقيد", "Clear plans without friction"],
    ["افتح صفحة الإثباتات", "Open Proof Page"],
    ["أسئلة شائعة قبل الاشتراك", "Frequently asked questions"],
    ["هل يضمن البوت الربح؟", "Does the bot guarantee profit?"],
    ["هل أحتاج خبرة؟", "Do I need experience?"],
    ["هل يمكن للبوت سحب أموالي؟", "Can the bot withdraw my funds?"],
    ["كيف أتأكد من البوت؟", "How do I verify the bot?"],
    ["هل يوجد دفع يدوي؟", "Is manual payment available?"],
    ["ماذا يحدث بعد التسجيل؟", "What happens after registration?"],
    ["روابط مهمة", "Important Links"],
    ["الأقسام", "Sections"],
    ["البريد الإلكتروني", "Email Address"],
    ["كلمة المرور", "Password"],
    ["الاسم الكامل", "Full Name"],
    ["اكتب اسمك الكامل", "Enter your full name"],
    ["أدخل كلمة مرور قوية", "Enter a strong password"],
    ["إظهار", "Show"],
    ["لديك حساب بالفعل؟", "Already have an account?"],
    ["ليس لديك حساب؟", "Do not have an account?"],
    ["نسيت كلمة المرور؟", "Forgot password?"],
    ["فتح البوت", "Open Bot"],
    ["تأكد من البوت الرسمي", "Verify the official bot"],
    ["تفعيل الحساب", "Verify Account"],
    ["كود التفعيل", "Verification Code"],
    ["تفعيل الآن", "Verify Now"],
    ["تم إنشاء الحساب", "Account Created"],
    ["حسابك جاهز للانطلاق", "Your account is ready"],
    ["الدفع", "Payment"],
    ["الدفع اليدوي", "Manual Payment"],
    ["سجل الفواتير", "Invoice History"],
    ["الدليل", "Guide"],
    ["المدفوعات", "Payments"],
    ["المستخدمين", "Users"],
    ["الإشارات", "Signals"],
    ["الإيرادات", "Revenue"],
    ["الخطة", "Plan"],
    ["الحالة", "Status"],
    ["تحديث", "Update"],
    ["حفظ", "Save"],
    ["إرسال", "Send"],
    ["إلغاء", "Cancel"],
    ["رجوع", "Back"],
    ["التالي", "Next"],
    ["السابق", "Previous"],
    ["تواصل معنا", "Contact"],
    ["من نحن", "About"],
    ["مركز الدعم", "Support Center"],
    ["التوثيق", "Documentation"],
    ["سياسة الخصوصية", "Privacy Policy"],
    ["الشروط", "Terms"],
    ["سياسة الاسترداد", "Refund Policy"],
    ["إخلاء مسؤولية المخاطر", "Risk Disclaimer"],
    ["سياسة الكوكيز", "Cookie Policy"]
  ];

  const arToEn = new Map(pairs);
  const enToAr = new Map(pairs.map(([ar, en]) => [en, ar]));
  const map = lang === "ar" ? enToAr : arToEn;
  const ignored = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE"]);

  const translateString = (value) => {
    if (!value || !value.trim()) return value;
    let output = value;
    for (const [from, to] of map.entries()) {
      output = output.split(from).join(to);
    }
    return output;
  };

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.parentElement || ignored.has(node.parentElement.tagName)) continue;
    nodes.push(node);
  }
  nodes.forEach((node) => {
    node.nodeValue = translateString(node.nodeValue);
  });

  document.querySelectorAll("[placeholder], [alt], [title], [aria-label], input[type='submit'], button").forEach((el) => {
    ["placeholder", "alt", "title", "aria-label", "value"].forEach((attr) => {
      if (el.hasAttribute(attr)) el.setAttribute(attr, translateString(el.getAttribute(attr)));
    });
  });
})();


// === NEXORA V3 ULTIMATE UI BOOT ===
(function(){
  function ready(fn){ if(document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  const root = document.documentElement;
  const saved = localStorage.getItem('nexora-theme');
  root.setAttribute('data-theme', saved || root.getAttribute('data-theme') || 'dark');
  ready(function(){
    const body = document.body;
    if(!body) return;
    if(document.querySelector('.page-wrap')) body.classList.add('nx-dashboard');
    if(document.querySelector('.admin-shell')) body.classList.add('nx-admin');
    if(document.querySelector('.login-box,.register-box,.success-box,.verify-box')) body.classList.add('nx-auth');
    if(location.pathname.includes('payment') || document.querySelector('.payment-box,.manual-box')) body.classList.add('nx-payment');
    if(location.pathname.includes('proof') || location.pathname.includes('bot-check')) body.classList.add('nx-proof');
    if(location.pathname.includes('system-health') || document.querySelector('.health-card,.status-card')) body.classList.add('nx-health');
    if(!document.querySelector('.theme-toggle')){
      const btn=document.createElement('button');
      btn.className='nx-floating-theme theme-toggle';
      btn.type='button';
      btn.setAttribute('aria-label','Toggle theme');
      btn.innerHTML='<span class="dark-icon">◐</span><span class="light-icon">☀</span>';
      document.body.appendChild(btn);
    }
    if(!document.querySelector('.nx-v3-orb')){
      const o1=document.createElement('div'); o1.className='nx-v3-orb';
      const o2=document.createElement('div'); o2.className='nx-v3-orb two';
      document.body.appendChild(o1); document.body.appendChild(o2);
    }
    document.addEventListener('click', function(e){
      const b=e.target.closest('.theme-toggle,.nx-floating-theme');
      if(!b) return;
      const next=(root.getAttribute('data-theme')==='light')?'dark':'light';
      root.setAttribute('data-theme', next); localStorage.setItem('nexora-theme', next);
    }, {capture:true});
    initMarketPreview();
    initTradingViewPreview();
  });

  function formatPrice(n){
    const x=Number(n); if(!isFinite(x)) return '--';
    if(x>1000) return x.toLocaleString(undefined,{maximumFractionDigits:2});
    if(x>1) return x.toLocaleString(undefined,{maximumFractionDigits:3});
    return x.toLocaleString(undefined,{maximumFractionDigits:5});
  }
  async function fetch24(symbol){
    const urls=[
      'https://api.binance.us/api/v3/ticker/24hr?symbol='+symbol,
      'https://api.binance.com/api/v3/ticker/24hr?symbol='+symbol
    ];
    for(const url of urls){
      try{ const r=await fetch(url,{cache:'no-store'}); if(r.ok) return await r.json(); }catch(e){}
    }
    return null;
  }
  function initMarketPreview(){
    const symbols=['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'];
    const strips=document.querySelectorAll('.premium-market-strip,.nx-live-strip');
    if(!strips.length && (document.querySelector('.hero') || document.querySelector('.dashboard-panel'))){
      const host=document.querySelector('.hero .container,.hero,.dashboard-panel,.page-wrap');
      if(host){
        const strip=document.createElement('div'); strip.className='nx-live-strip'; strip.setAttribute('aria-label','Live crypto prices');
        symbols.forEach(s=>{ const d=document.createElement('div'); d.className='nx-live-pill'; d.dataset.symbol=s; d.innerHTML='<strong>'+s.replace('USDT','/USDT')+'</strong><span>Loading...</span>'; strip.appendChild(d); });
        host.appendChild(strip);
      }
    }
    const pills=[...document.querySelectorAll('.premium-market-pill,.nx-live-pill')];
    if(!pills.length) return;
    const symbolFrom = (el) => (el.dataset.symbol || (el.querySelector('strong')?.textContent || '').replace('/','').replace(/\s/g,'')).toUpperCase();
    async function update(){
      for(const el of pills){
        let symbol=symbolFrom(el); if(!symbol.endsWith('USDT')) symbol+='USDT';
        const data=await fetch24(symbol);
        const span=el.querySelector('span') || el.appendChild(document.createElement('span'));
        if(data && data.lastPrice){
          const ch=Number(data.priceChangePercent||0);
          span.textContent='$'+formatPrice(data.lastPrice)+' '+(ch>=0?'+':'')+ch.toFixed(2)+'%';
          span.style.color=ch>=0?'var(--nx-green)':'var(--nx-red)';
        }
      }
    }
    update(); setInterval(update, 60000);
  }
  function initTradingViewPreview(){
    if(!document.querySelector('.hero') || document.querySelector('.nx-tv-wrap') || document.querySelector('.nx-trading-terminal')) return;
    const target=document.querySelector('main .section, .hero');
    if(!target) return;
    const wrap=document.createElement('section');
    wrap.className='nx-tv-wrap';
    wrap.innerHTML='<div class="nx-tv-head">Live Market Chart <span>BTCUSDT preview</span></div><iframe class="nx-tv-frame" title="TradingView BTCUSDT chart" loading="lazy" src="https://s.tradingview.com/widgetembed/?symbol=BINANCE%3ABTCUSDT&interval=60&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=111827&studies=[]&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&hideideas=1"></iframe>';
    target.parentNode.insertBefore(wrap, target.nextSibling);
  }
})();
