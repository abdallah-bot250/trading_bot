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

// === NEXORA MULTI-LANGUAGE UI LAYER ===
(function () {
  const root = document.documentElement;
  const current = (window.NEXORA_LANG || root.lang || "en").toLowerCase();
  const rtl = new Set(["ar", "ur"]);
  const languages = [
    { code: "en", native: "English", name: "English" },
    { code: "ar", native: "العربية", name: "Arabic" },
    { code: "es", native: "Español", name: "Spanish" },
    { code: "fr", native: "Français", name: "French" },
    { code: "de", native: "Deutsch", name: "German" },
    { code: "tr", native: "Türkçe", name: "Turkish" },
    { code: "pt", native: "Português", name: "Portuguese" },
    { code: "ru", native: "Русский", name: "Russian" },
    { code: "zh", native: "中文", name: "Chinese" },
    { code: "hi", native: "हिन्दी", name: "Hindi" },
    { code: "ur", native: "اردو", name: "Urdu" },
    { code: "id", native: "Bahasa Indonesia", name: "Indonesian" }
  ];

  const dict = {
    ar: {
      "Home": "الرئيسية", "Features": "المميزات", "Pricing": "الأسعار", "Proof": "الإثباتات", "Dashboard": "لوحة التحكم", "Login": "تسجيل الدخول", "Logout": "تسجيل الخروج", "Register": "إنشاء حساب", "Get Started": "ابدأ الآن", "Start Free Trial": "ابدأ التجربة المجانية", "Watch Demo": "شاهد العرض", "View Plans": "عرض الخطط", "Connect Telegram": "ربط تيليجرام", "Bot Check": "فحص البوت", "Manual Payment": "الدفع اليدوي", "Payment": "الدفع", "Payments": "المدفوعات", "Invoices": "الفواتير", "Profile": "الملف الشخصي", "Settings": "الإعدادات", "Support": "الدعم", "Support Center": "مركز الدعم", "Contact Support": "تواصل مع الدعم",
      "Current Plan": "الخطة الحالية", "Plan Status": "حالة الخطة", "Subscription Status": "حالة الاشتراك", "Remaining Days": "الأيام المتبقية", "Telegram Status": "حالة تيليجرام", "Connected": "متصل", "Not Connected": "غير متصل", "Active": "نشط", "Inactive": "غير نشط", "Free Trial": "تجربة مجانية", "Basic": "أساسي", "Pro": "احترافي", "Elite": "نخبة", "Pro 2 Years": "برو سنتين", "Upgrade": "ترقية", "Upgrade Plan": "ترقية الخطة",
      "Signals": "الإشارات", "Recent Signals": "آخر الإشارات", "Live Signals": "الإشارات المباشرة", "Get New Signals": "احصل على إشارات جديدة", "Auto Trading": "التداول التلقائي", "Risk Protection": "حماية المخاطر", "Signal Quality": "جودة الإشارة", "Confidence": "الثقة", "Win Rate": "نسبة النجاح", "Total Signals": "إجمالي الإشارات", "Open Trades": "الصفقات المفتوحة", "Closed Trades": "الصفقات المغلقة", "Performance": "الأداء", "AI Analysis": "تحليل الذكاء الاصطناعي",
      "Referral": "الإحالة", "Referrals": "الإحالات", "Invite & Earn": "ادع واربح", "Referral Link": "رابط الإحالة", "Copy": "نسخ", "Copied": "تم النسخ", "Free Earn": "اربح مجانًا", "Watch Video & Unlock": "شاهد الفيديو وافتح الإشارة", "Upgrade: No Ads": "ترقية بدون إعلانات",
      "Admin Overview": "نظرة عامة للأدمن", "Users": "المستخدمون", "Subscriptions": "الاشتراكات", "Revenue": "الإيرادات", "System Health": "صحة النظام", "Maintenance": "الصيانة", "Search users": "البحث عن المستخدمين", "Actions": "الإجراءات",
      "Email Address": "البريد الإلكتروني", "Password": "كلمة المرور", "Full Name": "الاسم الكامل", "Forgot password?": "نسيت كلمة المرور؟", "Create Account": "إنشاء حساب", "Already have an account?": "لديك حساب بالفعل؟", "Open Bot": "فتح البوت", "Verify Bot": "تأكيد البوت", "Save": "حفظ", "Cancel": "إلغاء", "Back": "رجوع", "Next": "التالي", "Send": "إرسال", "Language": "اللغة"
    },
    es: {
      "Home": "Inicio", "Features": "Funciones", "Pricing": "Precios", "Proof": "Pruebas", "Dashboard": "Panel", "Login": "Iniciar sesión", "Logout": "Salir", "Register": "Registro", "Get Started": "Empezar", "Start Free Trial": "Prueba gratis", "Watch Demo": "Ver demo", "View Plans": "Ver planes", "Connect Telegram": "Conectar Telegram", "Bot Check": "Verificar bot", "Manual Payment": "Pago manual", "Payment": "Pago", "Payments": "Pagos", "Invoices": "Facturas", "Profile": "Perfil", "Settings": "Ajustes", "Support": "Soporte",
      "Current Plan": "Plan actual", "Plan Status": "Estado del plan", "Subscription Status": "Estado de suscripción", "Remaining Days": "Días restantes", "Telegram Status": "Estado de Telegram", "Connected": "Conectado", "Not Connected": "No conectado", "Active": "Activo", "Inactive": "Inactivo", "Upgrade Plan": "Mejorar plan",
      "Signals": "Señales", "Recent Signals": "Señales recientes", "Live Signals": "Señales en vivo", "Auto Trading": "Trading automático", "Risk Protection": "Protección de riesgo", "Confidence": "Confianza", "Win Rate": "Tasa de acierto", "Total Signals": "Señales totales", "Performance": "Rendimiento", "AI Analysis": "Análisis de IA",
      "Referrals": "Referidos", "Invite & Earn": "Invita y gana", "Email Address": "Correo electrónico", "Password": "Contraseña", "Full Name": "Nombre completo", "Forgot password?": "¿Olvidaste tu contraseña?", "Create Account": "Crear cuenta", "Open Bot": "Abrir bot", "Save": "Guardar", "Cancel": "Cancelar", "Language": "Idioma"
    },
    fr: {
      "Home": "Accueil", "Features": "Fonctionnalités", "Pricing": "Tarifs", "Proof": "Preuves", "Dashboard": "Tableau de bord", "Login": "Connexion", "Logout": "Déconnexion", "Register": "Inscription", "Get Started": "Commencer", "Start Free Trial": "Essai gratuit", "Watch Demo": "Voir la démo", "View Plans": "Voir les plans", "Connect Telegram": "Connecter Telegram", "Bot Check": "Vérifier le bot", "Payment": "Paiement", "Payments": "Paiements", "Invoices": "Factures", "Profile": "Profil", "Settings": "Paramètres", "Support": "Support",
      "Current Plan": "Plan actuel", "Subscription Status": "Statut d'abonnement", "Remaining Days": "Jours restants", "Telegram Status": "Statut Telegram", "Connected": "Connecté", "Not Connected": "Non connecté", "Active": "Actif", "Upgrade Plan": "Améliorer le plan", "Signals": "Signaux", "Recent Signals": "Signaux récents", "Auto Trading": "Trading automatique", "Risk Protection": "Protection du risque", "Confidence": "Confiance", "Win Rate": "Taux de réussite", "Performance": "Performance", "AI Analysis": "Analyse IA", "Language": "Langue"
    },
    de: {
      "Home": "Start", "Features": "Funktionen", "Pricing": "Preise", "Proof": "Nachweise", "Dashboard": "Dashboard", "Login": "Anmelden", "Logout": "Abmelden", "Register": "Registrieren", "Get Started": "Loslegen", "Start Free Trial": "Kostenlos starten", "Watch Demo": "Demo ansehen", "View Plans": "Pläne ansehen", "Connect Telegram": "Telegram verbinden", "Payment": "Zahlung", "Payments": "Zahlungen", "Invoices": "Rechnungen", "Profile": "Profil", "Settings": "Einstellungen", "Support": "Support", "Current Plan": "Aktueller Plan", "Subscription Status": "Abo-Status", "Remaining Days": "Verbleibende Tage", "Telegram Status": "Telegram-Status", "Connected": "Verbunden", "Active": "Aktiv", "Signals": "Signale", "Recent Signals": "Letzte Signale", "Auto Trading": "Auto-Trading", "Risk Protection": "Risik Schutz", "Confidence": "Vertrauen", "Language": "Sprache"
    },
    tr: {
      "Home": "Ana Sayfa", "Features": "Özellikler", "Pricing": "Fiyatlar", "Proof": "Kanıt", "Dashboard": "Panel", "Login": "Giriş", "Logout": "Çıkış", "Register": "Kayıt", "Get Started": "Başla", "Start Free Trial": "Ücretsiz dene", "Watch Demo": "Demoyu izle", "View Plans": "Planları gör", "Connect Telegram": "Telegram bağla", "Payment": "Ödeme", "Payments": "Ödemeler", "Invoices": "Faturalar", "Profile": "Profil", "Settings": "Ayarlar", "Support": "Destek", "Current Plan": "Mevcut plan", "Subscription Status": "Abonelik durumu", "Remaining Days": "Kalan gün", "Telegram Status": "Telegram durumu", "Connected": "Bağlı", "Signals": "Sinyaller", "Recent Signals": "Son sinyaller", "Auto Trading": "Otomatik işlem", "Risk Protection": "Risk koruması", "Language": "Dil"
    },
    pt: {
      "Home": "Início", "Features": "Recursos", "Pricing": "Preços", "Proof": "Provas", "Dashboard": "Painel", "Login": "Entrar", "Logout": "Sair", "Register": "Registrar", "Get Started": "Começar", "Start Free Trial": "Teste grátis", "Watch Demo": "Ver demo", "View Plans": "Ver planos", "Connect Telegram": "Conectar Telegram", "Payment": "Pagamento", "Payments": "Pagamentos", "Invoices": "Faturas", "Profile": "Perfil", "Settings": "Configurações", "Support": "Suporte", "Current Plan": "Plano atual", "Subscription Status": "Status da assinatura", "Remaining Days": "Dias restantes", "Telegram Status": "Status do Telegram", "Connected": "Conectado", "Signals": "Sinais", "Recent Signals": "Sinais recentes", "Auto Trading": "Trading automático", "Risk Protection": "Proteção de risco", "Language": "Idioma"
    },
    ru: {
      "Home": "Главная", "Features": "Функции", "Pricing": "Цены", "Proof": "Доказательства", "Dashboard": "Панель", "Login": "Войти", "Logout": "Выйти", "Register": "Регистрация", "Get Started": "Начать", "Start Free Trial": "Бесплатный старт", "Watch Demo": "Смотреть демо", "View Plans": "Планы", "Connect Telegram": "Подключить Telegram", "Payment": "Оплата", "Payments": "Платежи", "Invoices": "Счета", "Profile": "Профиль", "Settings": "Настройки", "Support": "Поддержка", "Current Plan": "Текущий план", "Subscription Status": "Статус подписки", "Remaining Days": "Осталось дней", "Telegram Status": "Статус Telegram", "Connected": "Подключено", "Signals": "Сигналы", "Recent Signals": "Последние сигналы", "Auto Trading": "Автоторговля", "Risk Protection": "Защита риска", "Language": "Язык"
    },
    zh: {
      "Home": "首页", "Features": "功能", "Pricing": "价格", "Proof": "证明", "Dashboard": "控制台", "Login": "登录", "Logout": "退出", "Register": "注册", "Get Started": "开始", "Start Free Trial": "免费试用", "Watch Demo": "观看演示", "View Plans": "查看套餐", "Connect Telegram": "连接 Telegram", "Payment": "支付", "Payments": "付款", "Invoices": "发票", "Profile": "资料", "Settings": "设置", "Support": "支持", "Current Plan": "当前套餐", "Subscription Status": "订阅状态", "Remaining Days": "剩余天数", "Telegram Status": "Telegram 状态", "Connected": "已连接", "Signals": "信号", "Recent Signals": "最新信号", "Auto Trading": "自动交易", "Risk Protection": "风险保护", "Language": "语言"
    },
    hi: {
      "Home": "होम", "Features": "फीचर्स", "Pricing": "कीमत", "Proof": "प्रूफ", "Dashboard": "डैशबोर्ड", "Login": "लॉगिन", "Logout": "लॉगआउट", "Register": "रजिस्टर", "Get Started": "शुरू करें", "Start Free Trial": "फ्री ट्रायल", "Watch Demo": "डेमो देखें", "View Plans": "प्लान देखें", "Connect Telegram": "Telegram जोड़ें", "Payment": "भुगतान", "Payments": "भुगतान", "Invoices": "इनवॉइस", "Profile": "प्रोफाइल", "Settings": "सेटिंग्स", "Support": "सपोर्ट", "Current Plan": "मौजूदा प्लान", "Subscription Status": "सब्सक्रिप्शन स्थिति", "Remaining Days": "बचे दिन", "Telegram Status": "Telegram स्थिति", "Connected": "कनेक्टेड", "Signals": "सिग्नल", "Recent Signals": "हाल के सिग्नल", "Auto Trading": "ऑटो ट्रेडिंग", "Risk Protection": "रिस्क सुरक्षा", "Language": "भाषा"
    },
    ur: {
      "Home": "ہوم", "Features": "خصوصیات", "Pricing": "قیمتیں", "Proof": "ثبوت", "Dashboard": "ڈیش بورڈ", "Login": "لاگ ان", "Logout": "لاگ آؤٹ", "Register": "رجسٹر", "Get Started": "شروع کریں", "Start Free Trial": "مفت ٹرائل", "Watch Demo": "ڈیمو دیکھیں", "View Plans": "پلان دیکھیں", "Connect Telegram": "Telegram جوڑیں", "Payment": "ادائیگی", "Payments": "ادائیگیاں", "Invoices": "انوائسز", "Profile": "پروفائل", "Settings": "سیٹنگز", "Support": "سپورٹ", "Current Plan": "موجودہ پلان", "Subscription Status": "سبسکرپشن کی حالت", "Remaining Days": "باقی دن", "Telegram Status": "Telegram حالت", "Connected": "منسلک", "Signals": "سگنلز", "Recent Signals": "حالیہ سگنلز", "Auto Trading": "آٹو ٹریڈنگ", "Risk Protection": "رسک تحفظ", "Language": "زبان"
    },
    id: {
      "Home": "Beranda", "Features": "Fitur", "Pricing": "Harga", "Proof": "Bukti", "Dashboard": "Dasbor", "Login": "Masuk", "Logout": "Keluar", "Register": "Daftar", "Get Started": "Mulai", "Start Free Trial": "Coba gratis", "Watch Demo": "Lihat demo", "View Plans": "Lihat paket", "Connect Telegram": "Hubungkan Telegram", "Payment": "Pembayaran", "Payments": "Pembayaran", "Invoices": "Faktur", "Profile": "Profil", "Settings": "Pengaturan", "Support": "Dukungan", "Current Plan": "Paket saat ini", "Subscription Status": "Status langganan", "Remaining Days": "Sisa hari", "Telegram Status": "Status Telegram", "Connected": "Terhubung", "Signals": "Sinyal", "Recent Signals": "Sinyal terbaru", "Auto Trading": "Trading otomatis", "Risk Protection": "Perlindungan risiko", "Language": "Bahasa"
    }
  };

  function selectedLanguage() {
    return languages.find((item) => item.code === current) || languages[0];
  }

  function switchUrl(code) {
    const next = window.location.pathname + window.location.search;
    return "/set-language/" + encodeURIComponent(code) + "?next=" + encodeURIComponent(next);
  }

  function enhanceLanguageSwitchers() {
    document.querySelectorAll(".language-switcher").forEach((host) => {
      if (host.dataset.nexoraMultiLang === "ready") return;
      const active = selectedLanguage();
      host.dataset.nexoraMultiLang = "ready";
      host.classList.add("nx-language-menu");
      host.innerHTML = [
        '<button class="nx-language-current" type="button" aria-haspopup="true" aria-expanded="false">',
        '<span class="nx-language-globe">◎</span>',
        '<span class="nx-language-code">' + active.code.toUpperCase() + '</span>',
        '<span class="nx-language-name">' + active.native + '</span>',
        '<span class="nx-language-caret">⌄</span>',
        '</button>',
        '<div class="nx-language-list" role="menu">',
        languages.map((lang) => (
          '<a role="menuitem" class="' + (lang.code === current ? 'active' : '') + '" href="' + switchUrl(lang.code) + '">' +
          '<span class="nx-language-code">' + lang.code.toUpperCase() + '</span>' +
          '<span><strong>' + lang.native + '</strong><small>' + lang.name + '</small></span>' +
          '</a>'
        )).join(""),
        '</div>'
      ].join("");
    });
  }

  function translateText(value, map) {
    if (!value || !value.trim()) return value;
    let output = value;
    const keys = Object.keys(map).sort((a, b) => b.length - a.length);
    keys.forEach((key) => {
      output = output.split(key).join(map[key]);
    });
    return output;
  }

  function translatePage() {
    const map = dict[current];
    if (!map) return;
    const ignored = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT"]);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentElement || ignored.has(node.parentElement.tagName)) continue;
      if (node.parentElement.closest("[data-no-translate], .no-translate, .nx-language-menu")) continue;
      nodes.push(node);
    }
    nodes.forEach((node) => {
      node.nodeValue = translateText(node.nodeValue, map);
    });
    document.querySelectorAll("[placeholder], [alt], [title], [aria-label], input[type='submit']").forEach((el) => {
      if (el.closest("[data-no-translate], .no-translate, .nx-language-menu")) return;
      ["placeholder", "alt", "title", "aria-label", "value"].forEach((attr) => {
        if (el.hasAttribute(attr)) el.setAttribute(attr, translateText(el.getAttribute(attr), map));
      });
    });
    if (document.title) document.title = translateText(document.title, map);
  }

  root.lang = current;
  root.dir = rtl.has(current) ? "rtl" : "ltr";
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".nx-language-current");
    if (!button) return;
    const menu = button.closest(".nx-language-menu");
    const open = menu.classList.toggle("open");
    button.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest(".nx-language-menu")) return;
    document.querySelectorAll(".nx-language-menu.open").forEach((menu) => menu.classList.remove("open"));
  });
  const run = () => {
    enhanceLanguageSwitchers();
    translatePage();
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
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
    document.querySelectorAll('.nx-tv-wrap').forEach(function(el){ el.remove(); });
    return;
  }
})();
