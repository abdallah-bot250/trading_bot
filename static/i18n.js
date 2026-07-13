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

// === NEXORA EXTENDED PAGE COPY TRANSLATION PACK ===
(function () {
  const root = document.documentElement;
  const lang = (window.NEXORA_LANG || root.lang || "en").toLowerCase();
  if (lang === "en") return;

  const copy = {
    ar: {
      "Nexora AI Trader is a risk-managed AI crypto signal platform with SMC, support and resistance targets, Telegram delivery, dashboard tracking, and a free trial.": "Nexora AI Trader منصة إشارات كريبتو مدعومة بالذكاء الاصطناعي مع إدارة مخاطر، أهداف دعم ومقاومة، توصيل عبر تيليجرام، تتبع من الداشبورد، وتجربة مجانية.",
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "منصة إشارات كريبتو مدعومة بالذكاء الاصطناعي مع تنبيهات تيليجرام وإدارة مخاطر وتتبع من الداشبورد.",
      "AI crypto signal platform for serious traders": "منصة إشارات كريبتو ذكية للمتداول الجاد",
      "Professional BTC/USDT trading terminal.": "منصة تداول احترافية BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "عرض TradingView كامل لقراءة الاتجاه وحركة السعر ومراجعة السوق قبل فتح الداشبورد.",
      "Built for traders who want clarity before entry.": "مصمم للمتداولين الذين يريدون وضوحًا قبل الدخول.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "تركز المنصة على دعم القرار وجودة الإشارة ووضوح الأهداف بدل التنبيهات العشوائية.",
      "A simple flow from website to Telegram to dashboard.": "رحلة بسيطة من الموقع إلى تيليجرام ثم الداشبورد.",
      "More than signals. A full AI trading workspace.": "أكثر من إشارات. مساحة تداول كاملة مدعومة بالذكاء الاصطناعي.",
      "Rules, paper trading, AI optimization, strategy templates, exchanges, executions, academy, and platform tools.": "قواعد تداول، تجربة ورقية، تحسينات ذكاء اصطناعي، قوالب استراتيجيات، منصات، تنفيذ، أكاديمية، وأدوات للمنصة.",
      "Built to feel like a trading automation platform, positioned around safer AI signal delivery.": "مصمم ليبدو كمنصة أتمتة تداول احترافية مع تركيز على توصيل إشارات AI أكثر أمانًا.",
      "Clear plans without renaming production plan IDs.": "خطط واضحة بدون تغيير معرفات الخطط الإنتاجية.",
      "Choose the plan that matches your usage. Manual payment stays available.": "اختر الخطة المناسبة لاستخدامك. الدفع اليدوي متاح دائمًا.",
      "Review examples before subscribing.": "راجع الأمثلة قبل الاشتراك.",
      "Use the proof page and official bot check to verify what the platform shows. Avoid fake Telegram accounts and never trust guaranteed profit claims.": "استخدم صفحة الإثبات وفحص البوت الرسمي للتحقق من المنصة. تجنب حسابات تيليجرام المزيفة ولا تثق بأي وعود ربح مضمونة.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader برنامج لدعم القرار. تداول العملات الرقمية عالي المخاطر. الإشارات والداشبورد وتحليل الذكاء الاصطناعي لا تضمن الربح. أدِر رأس مالك واتخذ قرارك النهائي بنفسك.",
      "Animated dashboard preview built around real product workflows.": "معاينة داشبورد متحركة مبنية على تدفقات المنتج الحقيقية.",
      "No fake profit guarantees. The interface highlights plan status, Telegram linking, signal quality, and performance tracking.": "بدون وعود أرباح وهمية. الواجهة تعرض حالة الخطة، ربط تيليجرام، جودة الإشارات، وتتبع الأداء.",
      "Performance is displayed only when tracked data exists.": "يتم عرض الأداء فقط عند وجود بيانات تتبع حقيقية.",
      "Nexora avoids fake results. New accounts see clear empty states until real signals and closed outcomes are recorded.": "Nexora يتجنب النتائج الوهمية. الحسابات الجديدة ترى حالات فارغة واضحة حتى يتم تسجيل إشارات ونتائج مغلقة حقيقية.",
      "Built with production safety in mind.": "مصمم مع مراعاة أمان الإنتاج.",
      "A clear path for buyers and operators.": "مسار واضح للمشترين والمشغلين.",
      "Use verified customer quotes when available.": "استخدم آراء عملاء موثقة عند توفرها.",
      "Until real testimonials are approved, this section stays honest and product-focused.": "حتى يتم اعتماد شهادات حقيقية، يظل هذا القسم صادقًا ومركزًا على المنتج.",
      "Common questions before subscribing.": "أسئلة شائعة قبل الاشتراك.",
      "Does Nexora guarantee profit?": "هل تضمن Nexora الربح؟",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "لا. تقدم تحليل سوق مدعوم بالذكاء الاصطناعي وتنبيهات منظمة. نتائج التداول غير مضمونة.",
      "How do I receive signals?": "كيف أستقبل الإشارات؟",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "أنشئ حسابًا، اربط البوت الرسمي على تيليجرام، وحافظ على الاتصال من الداشبورد.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "ذكاء إشارات كريبتو احترافي مع توصيل مُدار بالمخاطر، ربط تيليجرام، وداشبورد نظيف.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "أنشئ حسابك مباشرة، ثم اربط تيليجرام من الداشبورد أو البوت الرسمي."
    },
    es: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plataforma de señales cripto asistida por IA con alertas de Telegram gestionadas por riesgo y seguimiento en panel.",
      "AI crypto signal platform for serious traders": "Plataforma de señales cripto con IA para traders serios",
      "Professional BTC/USDT trading terminal.": "Terminal profesional de trading BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vista completa de TradingView para contexto del gráfico, lectura de tendencia y revisión del precio antes de abrir el panel.",
      "Built for traders who want clarity before entry.": "Creado para traders que quieren claridad antes de entrar.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "La plataforma prioriza soporte de decisión, señales más limpias y objetivos transparentes en lugar de alertas ruidosas.",
      "A simple flow from website to Telegram to dashboard.": "Un flujo simple del sitio web a Telegram y luego al panel.",
      "More than signals. A full AI trading workspace.": "Más que señales. Un espacio completo de trading con IA.",
      "Clear plans without renaming production plan IDs.": "Planes claros sin renombrar los IDs de producción.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Elige el plan que se adapte a tu uso. El pago manual sigue disponible.",
      "Review examples before subscribing.": "Revisa ejemplos antes de suscribirte.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader es software de apoyo a decisiones. El trading cripto implica riesgo. Las señales, paneles y análisis de IA no garantizan ganancias.",
      "Performance is displayed only when tracked data exists.": "El rendimiento solo se muestra cuando existen datos reales rastreados.",
      "Common questions before subscribing.": "Preguntas frecuentes antes de suscribirse.",
      "Does Nexora guarantee profit?": "¿Nexora garantiza ganancias?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "No. Proporciona análisis de mercado asistido por IA y alertas estructuradas. Los resultados nunca están garantizados.",
      "How do I receive signals?": "¿Cómo recibo señales?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Crea una cuenta, vincula el bot oficial de Telegram y mantenlo conectado desde tu panel.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Inteligencia premium de señales cripto con entrega gestionada por riesgo, conexión Telegram y panel limpio.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Crea tu cuenta directamente y luego vincula Telegram desde el panel o el bot oficial."
    },
    fr: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plateforme de signaux crypto assistée par IA avec alertes Telegram à risque maîtrisé et suivi dans le tableau de bord.",
      "AI crypto signal platform for serious traders": "Plateforme de signaux crypto IA pour traders sérieux",
      "Professional BTC/USDT trading terminal.": "Terminal de trading BTC/USDT professionnel.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vue TradingView pleine largeur pour analyser le graphique, la tendance et l'action des prix avant d'ouvrir le tableau de bord.",
      "Built for traders who want clarity before entry.": "Conçu pour les traders qui veulent de la clarté avant l'entrée.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "La plateforme privilégie l'aide à la décision, la qualité des signaux et des objectifs transparents plutôt que des alertes bruyantes.",
      "A simple flow from website to Telegram to dashboard.": "Un parcours simple du site vers Telegram puis le tableau de bord.",
      "More than signals. A full AI trading workspace.": "Plus que des signaux. Un espace de trading IA complet.",
      "Clear plans without renaming production plan IDs.": "Des plans clairs sans renommer les IDs de production.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Choisissez le plan adapté à votre usage. Le paiement manuel reste disponible.",
      "Review examples before subscribing.": "Consultez les exemples avant de vous abonner.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader est un logiciel d'aide à la décision. Le trading crypto est risqué. Les signaux, tableaux de bord et analyses IA ne garantissent pas de profits.",
      "Performance is displayed only when tracked data exists.": "La performance s'affiche uniquement lorsque des données suivies existent.",
      "Common questions before subscribing.": "Questions fréquentes avant l'abonnement.",
      "Does Nexora guarantee profit?": "Nexora garantit-il des profits ?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Non. Il fournit une analyse de marché assistée par IA et des alertes structurées. Les résultats ne sont jamais garantis.",
      "How do I receive signals?": "Comment recevoir les signaux ?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Créez un compte, liez le bot Telegram officiel et gardez-le connecté depuis votre tableau de bord.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Intelligence premium de signaux crypto avec livraison maîtrisée, connexion Telegram et tableau de bord clair.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Créez votre compte directement, puis liez Telegram depuis le tableau de bord ou le bot officiel."
    },
    de: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "KI-gestützte Krypto-Signalplattform mit risikogesteuerten Telegram-Alerts und Dashboard-Tracking.",
      "AI crypto signal platform for serious traders": "KI-Krypto-Signalplattform für ernsthafte Trader",
      "Professional BTC/USDT trading terminal.": "Professionelles BTC/USDT-Trading-Terminal.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vollbreite TradingView-Ansicht für Chart-Kontext, Trendanalyse und Price-Action-Prüfung vor dem Dashboard.",
      "Built for traders who want clarity before entry.": "Für Trader gebaut, die vor dem Einstieg Klarheit wollen.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Die Plattform fokussiert Entscheidungshilfe, saubere Signalqualität und transparente Ziele statt lauter Alerts.",
      "A simple flow from website to Telegram to dashboard.": "Ein einfacher Ablauf von Website zu Telegram zum Dashboard.",
      "More than signals. A full AI trading workspace.": "Mehr als Signale. Ein kompletter KI-Trading-Arbeitsbereich.",
      "Clear plans without renaming production plan IDs.": "Klare Pläne ohne Umbenennung produktiver Plan-IDs.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Wählen Sie den passenden Plan. Manuelle Zahlung bleibt verfügbar.",
      "Review examples before subscribing.": "Prüfen Sie Beispiele vor dem Abonnieren.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader ist Entscheidungssoftware. Krypto-Trading ist riskant. Signale, Dashboards und KI-Analysen garantieren keine Gewinne.",
      "Performance is displayed only when tracked data exists.": "Performance wird nur angezeigt, wenn echte Tracking-Daten vorhanden sind.",
      "Common questions before subscribing.": "Häufige Fragen vor dem Abo.",
      "Does Nexora guarantee profit?": "Garantiert Nexora Gewinn?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Nein. Es bietet KI-gestützte Marktanalyse und strukturierte Alerts. Ergebnisse sind nie garantiert.",
      "How do I receive signals?": "Wie erhalte ich Signale?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Konto erstellen, offiziellen Telegram-Bot verbinden und im Dashboard verbunden halten.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Premium-Krypto-Signalintelligenz mit risikogesteuerter Zustellung, Telegram-Verbindung und klarem Dashboard.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Erstellen Sie Ihr Konto direkt und verbinden Sie Telegram danach im Dashboard oder offiziellen Bot."
    },
    tr: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Risk yönetimli Telegram uyarıları ve panel takibi olan yapay zekâ destekli kripto sinyal platformu.",
      "AI crypto signal platform for serious traders": "Ciddi yatırımcılar için yapay zekâ kripto sinyal platformu",
      "Professional BTC/USDT trading terminal.": "Profesyonel BTC/USDT işlem terminali.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Kullanıcılar panele girmeden önce grafik bağlamı, trend ve fiyat hareketini incelemek için tam genişlik TradingView görünümü.",
      "Built for traders who want clarity before entry.": "İşleme girmeden önce netlik isteyen traderlar için tasarlandı.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Platform gürültülü uyarılar yerine karar desteği, temiz sinyal kalitesi ve şeffaf hedeflere odaklanır.",
      "A simple flow from website to Telegram to dashboard.": "Web sitesinden Telegram'a ve ardından panele uzanan basit akış.",
      "More than signals. A full AI trading workspace.": "Sinyallerden fazlası. Tam bir yapay zekâ işlem alanı.",
      "Clear plans without renaming production plan IDs.": "Üretim plan kimliklerini değiştirmeden net planlar.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Kullanımınıza uygun planı seçin. Manuel ödeme kullanılabilir kalır.",
      "Review examples before subscribing.": "Abone olmadan önce örnekleri inceleyin.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader karar destek yazılımıdır. Kripto işlemleri risklidir. Sinyaller ve analizler kâr garantisi vermez.",
      "Performance is displayed only when tracked data exists.": "Performans yalnızca takip edilen gerçek veri varsa gösterilir.",
      "Common questions before subscribing.": "Abonelik öncesi sık sorular.",
      "Does Nexora guarantee profit?": "Nexora kâr garantisi verir mi?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Hayır. Yapay zekâ destekli piyasa analizi ve yapılandırılmış uyarılar sunar. Sonuçlar garanti değildir.",
      "How do I receive signals?": "Sinyalleri nasıl alırım?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Hesap oluşturun, resmi Telegram botunu bağlayın ve panelden bağlı tutun.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Risk yönetimli gönderim, Telegram bağlantısı ve temiz panel ile premium kripto sinyal zekâsı.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Hesabınızı doğrudan oluşturun, ardından panelden veya resmi bottan Telegram'ı bağlayın."
    },
    pt: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plataforma de sinais cripto com IA, alertas Telegram com gestão de risco e acompanhamento no painel.",
      "AI crypto signal platform for serious traders": "Plataforma de sinais cripto com IA para traders sérios",
      "Professional BTC/USDT trading terminal.": "Terminal profissional de trading BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Visão TradingView em largura total para contexto do gráfico, leitura de tendência e revisão do preço antes do painel.",
      "Built for traders who want clarity before entry.": "Criado para traders que querem clareza antes da entrada.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "A plataforma foca em apoio à decisão, qualidade de sinal e alvos transparentes em vez de alertas ruidosos.",
      "A simple flow from website to Telegram to dashboard.": "Um fluxo simples do site para o Telegram e depois para o painel.",
      "More than signals. A full AI trading workspace.": "Mais que sinais. Um espaço completo de trading com IA.",
      "Clear plans without renaming production plan IDs.": "Planos claros sem renomear IDs de produção.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Escolha o plano que combina com seu uso. Pagamento manual continua disponível.",
      "Review examples before subscribing.": "Revise exemplos antes de assinar.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader é software de apoio à decisão. Trading cripto é arriscado. Sinais e análises não garantem lucro.",
      "Performance is displayed only when tracked data exists.": "O desempenho só aparece quando existem dados reais rastreados.",
      "Common questions before subscribing.": "Perguntas comuns antes da assinatura.",
      "Does Nexora guarantee profit?": "A Nexora garante lucro?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Não. Ela fornece análise de mercado com IA e alertas estruturados. Resultados nunca são garantidos.",
      "How do I receive signals?": "Como recebo sinais?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Crie uma conta, conecte o bot oficial do Telegram e mantenha-o conectado no painel.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Inteligência premium de sinais cripto com entrega gerida por risco, Telegram e painel limpo.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Crie sua conta diretamente e depois conecte o Telegram pelo painel ou bot oficial."
    },
    ru: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Платформа крипто-сигналов с ИИ, Telegram-уведомлениями с контролем риска и отслеживанием в панели.",
      "AI crypto signal platform for serious traders": "Платформа ИИ крипто-сигналов для серьезных трейдеров",
      "Professional BTC/USDT trading terminal.": "Профессиональный торговый терминал BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Полноширинный TradingView для анализа графика, тренда и движения цены перед открытием панели.",
      "Built for traders who want clarity before entry.": "Создано для трейдеров, которым нужна ясность перед входом.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Платформа делает акцент на поддержке решений, качестве сигналов и прозрачных целях вместо шумных уведомлений.",
      "A simple flow from website to Telegram to dashboard.": "Простой путь: сайт, Telegram, затем панель.",
      "More than signals. A full AI trading workspace.": "Больше, чем сигналы. Полное рабочее пространство трейдинга с ИИ.",
      "Clear plans without renaming production plan IDs.": "Понятные планы без переименования production ID.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Выберите план под ваши задачи. Ручная оплата доступна.",
      "Review examples before subscribing.": "Посмотрите примеры перед подпиской.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader — ПО для поддержки решений. Криптотрейдинг рискован. Сигналы и ИИ-анализ не гарантируют прибыль.",
      "Performance is displayed only when tracked data exists.": "Показатели отображаются только при наличии реальных данных.",
      "Common questions before subscribing.": "Частые вопросы перед подпиской.",
      "Does Nexora guarantee profit?": "Nexora гарантирует прибыль?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Нет. Она дает ИИ-анализ рынка и структурированные уведомления. Результаты не гарантируются.",
      "How do I receive signals?": "Как получать сигналы?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Создайте аккаунт, подключите официальный Telegram-бот и держите его подключенным в панели.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Премиальная аналитика крипто-сигналов с контролем риска, Telegram и удобной панелью.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Создайте аккаунт, затем подключите Telegram через панель или официальный бот."
    },
    zh: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "由 AI 辅助的加密信号平台，提供风险管理的 Telegram 提醒和仪表盘跟踪。",
      "AI crypto signal platform for serious traders": "面向专业交易者的 AI 加密信号平台",
      "Professional BTC/USDT trading terminal.": "专业 BTC/USDT 交易终端。",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "全宽 TradingView 市场视图，用于在进入仪表盘前查看图表、趋势和价格行为。",
      "Built for traders who want clarity before entry.": "为希望在入场前获得清晰判断的交易者打造。",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "平台专注于决策支持、更干净的信号质量和透明目标，而不是噪音提醒。",
      "A simple flow from website to Telegram to dashboard.": "从网站到 Telegram 再到仪表盘的简单流程。",
      "More than signals. A full AI trading workspace.": "不只是信号，而是完整的 AI 交易工作区。",
      "Clear plans without renaming production plan IDs.": "清晰套餐，不改变生产计划 ID。",
      "Choose the plan that matches your usage. Manual payment stays available.": "选择适合你使用方式的套餐。仍支持手动付款。",
      "Review examples before subscribing.": "订阅前先查看示例。",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader 是决策辅助软件。加密交易有风险，信号、仪表盘和 AI 分析不保证盈利。",
      "Performance is displayed only when tracked data exists.": "只有存在真实跟踪数据时才显示表现。",
      "Common questions before subscribing.": "订阅前常见问题。",
      "Does Nexora guarantee profit?": "Nexora 保证盈利吗？",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "不保证。它提供 AI 辅助市场分析和结构化提醒，交易结果永远无法保证。",
      "How do I receive signals?": "如何接收信号？",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "创建账户，绑定官方 Telegram 机器人，并在仪表盘保持连接。",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "高级加密信号智能，支持风险管理投递、Telegram 连接和清晰仪表盘。",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "直接创建账户，然后从仪表盘或官方机器人绑定 Telegram。"
    },
    hi: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "AI-सहायता वाली क्रिप्टो सिग्नल प्लेटफॉर्म, जोखिम-प्रबंधित Telegram अलर्ट और डैशबोर्ड ट्रैकिंग के साथ।",
      "AI crypto signal platform for serious traders": "गंभीर ट्रेडरों के लिए AI क्रिप्टो सिग्नल प्लेटफॉर्म",
      "Professional BTC/USDT trading terminal.": "प्रोफेशनल BTC/USDT ट्रेडिंग टर्मिनल।",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "डैशबोर्ड खोलने से पहले चार्ट, ट्रेंड और प्राइस एक्शन देखने के लिए फुल-विथ TradingView व्यू।",
      "Built for traders who want clarity before entry.": "उन ट्रेडरों के लिए बनाया गया जो एंट्री से पहले स्पष्टता चाहते हैं।",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "प्लेटफॉर्म शोर वाले अलर्ट की जगह निर्णय सहायता, बेहतर सिग्नल गुणवत्ता और साफ लक्ष्यों पर केंद्रित है।",
      "A simple flow from website to Telegram to dashboard.": "वेबसाइट से Telegram और फिर डैशबोर्ड तक सरल प्रवाह।",
      "More than signals. A full AI trading workspace.": "सिग्नल से अधिक। पूरा AI ट्रेडिंग वर्कस्पेस।",
      "Clear plans without renaming production plan IDs.": "प्रोडक्शन प्लान IDs बदले बिना साफ प्लान।",
      "Choose the plan that matches your usage. Manual payment stays available.": "अपने उपयोग के अनुसार प्लान चुनें। मैनुअल पेमेंट उपलब्ध रहता है।",
      "Review examples before subscribing.": "सब्सक्राइब करने से पहले उदाहरण देखें।",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader निर्णय-सहायता सॉफ्टवेयर है। क्रिप्टो ट्रेडिंग जोखिमपूर्ण है। सिग्नल और AI विश्लेषण लाभ की गारंटी नहीं देते।",
      "Performance is displayed only when tracked data exists.": "प्रदर्शन तभी दिखता है जब वास्तविक ट्रैक डेटा मौजूद हो।",
      "Common questions before subscribing.": "सब्सक्रिप्शन से पहले सामान्य प्रश्न।",
      "Does Nexora guarantee profit?": "क्या Nexora लाभ की गारंटी देता है?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "नहीं। यह AI-सहायता वाला मार्केट विश्लेषण और संरचित अलर्ट देता है। परिणामों की गारंटी नहीं होती।",
      "How do I receive signals?": "मुझे सिग्नल कैसे मिलेंगे?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "खाता बनाएं, आधिकारिक Telegram bot लिंक करें और डैशबोर्ड से कनेक्ट रखें।",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "जोखिम-प्रबंधित डिलीवरी, Telegram कनेक्शन और साफ डैशबोर्ड के साथ प्रीमियम क्रिप्टो सिग्नल इंटेलिजेंस।",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "सीधे खाता बनाएं, फिर डैशबोर्ड या आधिकारिक bot से Telegram लिंक करें।"
    },
    ur: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "AI کی مدد سے کرپٹو سگنل پلیٹ فارم، رسک مینجڈ Telegram الرٹس اور ڈیش بورڈ ٹریکنگ کے ساتھ۔",
      "AI crypto signal platform for serious traders": "سنجیدہ ٹریڈرز کے لیے AI کرپٹو سگنل پلیٹ فارم",
      "Professional BTC/USDT trading terminal.": "پروفیشنل BTC/USDT ٹریڈنگ ٹرمینل۔",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "ڈیش بورڈ کھولنے سے پہلے چارٹ، ٹرینڈ اور پرائس ایکشن کے لیے مکمل TradingView مارکیٹ ویو۔",
      "Built for traders who want clarity before entry.": "ان ٹریڈرز کے لیے جو انٹری سے پہلے واضح فیصلہ چاہتے ہیں۔",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "یہ پلیٹ فارم شور والے الرٹس کے بجائے فیصلہ سازی، بہتر سگنل کوالٹی اور واضح اہداف پر توجہ دیتا ہے۔",
      "A simple flow from website to Telegram to dashboard.": "ویب سائٹ سے Telegram اور پھر ڈیش بورڈ تک آسان فلو۔",
      "More than signals. A full AI trading workspace.": "صرف سگنلز نہیں، مکمل AI ٹریڈنگ ورک اسپیس۔",
      "Clear plans without renaming production plan IDs.": "پروڈکشن پلان IDs بدلے بغیر واضح پلانز۔",
      "Choose the plan that matches your usage. Manual payment stays available.": "اپنے استعمال کے مطابق پلان منتخب کریں۔ دستی ادائیگی دستیاب رہتی ہے۔",
      "Review examples before subscribing.": "سبسکرائب کرنے سے پہلے مثالیں دیکھیں۔",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader فیصلہ سازی میں مدد دینے والا سافٹ ویئر ہے۔ کرپٹو ٹریڈنگ خطرناک ہے۔ سگنلز اور AI تجزیہ منافع کی ضمانت نہیں دیتے۔",
      "Performance is displayed only when tracked data exists.": "کارکردگی صرف تب دکھائی جاتی ہے جب حقیقی ٹریک شدہ ڈیٹا موجود ہو۔",
      "Common questions before subscribing.": "سبسکرائب کرنے سے پہلے عام سوالات۔",
      "Does Nexora guarantee profit?": "کیا Nexora منافع کی ضمانت دیتا ہے؟",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "نہیں۔ یہ AI مارکیٹ تجزیہ اور منظم الرٹس فراہم کرتا ہے۔ نتائج کبھی ضمانت شدہ نہیں ہوتے۔",
      "How do I receive signals?": "مجھے سگنلز کیسے ملیں گے؟",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "اکاؤنٹ بنائیں، آفیشل Telegram bot لنک کریں، اور ڈیش بورڈ سے اسے کنیکٹ رکھیں۔",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "رسک مینجڈ ڈیلیوری، Telegram کنکشن اور صاف ڈیش بورڈ کے ساتھ پریمیم کرپٹو سگنل انٹیلیجنس۔",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "اپنا اکاؤنٹ براہ راست بنائیں، پھر ڈیش بورڈ یا آفیشل bot سے Telegram لنک کریں۔"
    },
    id: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Platform sinyal kripto berbantuan AI dengan alert Telegram berbasis manajemen risiko dan pelacakan dasbor.",
      "AI crypto signal platform for serious traders": "Platform sinyal kripto AI untuk trader serius",
      "Professional BTC/USDT trading terminal.": "Terminal trading BTC/USDT profesional.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Tampilan TradingView penuh untuk konteks grafik, pembacaan tren, dan review price action sebelum membuka dasbor.",
      "Built for traders who want clarity before entry.": "Dibuat untuk trader yang ingin kejelasan sebelum entry.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Platform berfokus pada dukungan keputusan, kualitas sinyal lebih bersih, dan target transparan, bukan alert yang bising.",
      "A simple flow from website to Telegram to dashboard.": "Alur sederhana dari website ke Telegram lalu ke dasbor.",
      "More than signals. A full AI trading workspace.": "Lebih dari sinyal. Workspace trading AI lengkap.",
      "Clear plans without renaming production plan IDs.": "Paket jelas tanpa mengganti ID paket produksi.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Pilih paket sesuai penggunaan Anda. Pembayaran manual tetap tersedia.",
      "Review examples before subscribing.": "Lihat contoh sebelum berlangganan.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader adalah software pendukung keputusan. Trading kripto berisiko. Sinyal dan analisis AI tidak menjamin profit.",
      "Performance is displayed only when tracked data exists.": "Performa hanya ditampilkan ketika data nyata tersedia.",
      "Common questions before subscribing.": "Pertanyaan umum sebelum berlangganan.",
      "Does Nexora guarantee profit?": "Apakah Nexora menjamin profit?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Tidak. Nexora menyediakan analisis pasar berbantuan AI dan alert terstruktur. Hasil trading tidak pernah dijamin.",
      "How do I receive signals?": "Bagaimana saya menerima sinyal?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Buat akun, hubungkan bot Telegram resmi, dan jaga koneksi dari dasbor.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Intelijen sinyal kripto premium dengan pengiriman berbasis risiko, koneksi Telegram, dan dasbor bersih.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Buat akun langsung, lalu hubungkan Telegram dari dasbor atau bot resmi."
    }
  };

  const phrases = copy[lang];
  if (!phrases) return;
  const ignored = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT"]);
  const keys = Object.keys(phrases).sort((a, b) => b.length - a.length);

  function translateValue(value) {
    if (!value || !value.trim()) return value;
    let next = value;
    keys.forEach((key) => {
      next = next.split(key).join(phrases[key]);
    });
    return next;
  }

  function runExtendedCopyTranslation() {
    if (!document.body) return;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentElement || ignored.has(node.parentElement.tagName)) continue;
      if (node.parentElement.closest("[data-no-translate], .no-translate, .nx-language-menu")) continue;
      nodes.push(node);
    }
    nodes.forEach((node) => {
      node.nodeValue = translateValue(node.nodeValue);
    });
    document.querySelectorAll("[placeholder], [alt], [title], [aria-label], input[type='submit']").forEach((el) => {
      if (el.closest("[data-no-translate], .no-translate, .nx-language-menu")) return;
      ["placeholder", "alt", "title", "aria-label", "value"].forEach((attr) => {
        if (el.hasAttribute(attr)) el.setAttribute(attr, translateValue(el.getAttribute(attr)));
      });
    });
    if (document.title) document.title = translateValue(document.title);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runExtendedCopyTranslation);
  } else {
    runExtendedCopyTranslation();
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
