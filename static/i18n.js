(() => {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("nexora-theme");
  root.setAttribute("data-theme", savedTheme || "dark");

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".theme-toggle, .nx-floating-theme");
    if (!button) return;
    const currentTheme = root.getAttribute("data-theme") || "dark";
    const nextTheme = currentTheme === "light" ? "dark" : "light";
    root.setAttribute("data-theme", nextTheme);
    localStorage.setItem("nexora-theme", nextTheme);
  });
})();

// === NEXORA CLEAN MULTI-LANGUAGE UI LAYER ===
(function () {
  const root = document.documentElement;
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

  const current = normalizeLanguage(window.NEXORA_LANG || root.lang || "en");

  const arToEn = {
    "الرئيسية": "Home",
    "المميزات": "Features",
    "الأسعار": "Pricing",
    "الإثباتات": "Proof",
    "تجارب المستخدمين": "User Proof",
    "فحص البوت": "Bot Check",
    "تأكد من البوت": "Verify Bot",
    "لوحة التحكم": "Dashboard",
    "الداشبورد": "Dashboard",
    "دخول": "Login",
    "تسجيل الدخول": "Login",
    "تسجيل الخروج": "Logout",
    "إنشاء حساب": "Create Account",
    "إنشاء حساب جديد": "Create Account",
    "ابدأ الآن": "Get Started",
    "ابدأ التجربة": "Start Trial",
    "ابدأ التجربة المجانية": "Start Free Trial",
    "شاهد الديمو": "View Demo",
    "شاهد العرض": "Watch Demo",
    "شاهد النتائج": "View Results",
    "منصة إشارات كريبتو ذكية للمتداول الجاد": "AI crypto signal platform for serious traders",
    "إشارات منتقاة": "Curated Signals",
    "لوحة تحكم كاملة": "Complete Dashboard",
    "ربط تيليجرام": "Telegram Linking",
    "دفع يدوي وأوتوماتيك": "Manual and Automatic Payments",
    "تجربة مجانية": "Free Trial",
    "كيف يفكر النظام؟": "How the system thinks",
    "اختبر النظام": "Try the System",
    "خطط واضحة بدون تعقيد": "Clear plans without friction",
    "افتح صفحة الإثباتات": "Open Proof Page",
    "أسئلة شائعة قبل الاشتراك": "Frequently asked questions",
    "هل يضمن البوت الربح؟": "Does the bot guarantee profit?",
    "هل أحتاج خبرة؟": "Do I need experience?",
    "هل يمكن للبوت سحب أموالي؟": "Can the bot withdraw my funds?",
    "كيف أتأكد من البوت؟": "How do I verify the bot?",
    "هل يوجد دفع يدوي؟": "Is manual payment available?",
    "ماذا يحدث بعد التسجيل؟": "What happens after registration?",
    "روابط مهمة": "Important Links",
    "الأقسام": "Sections",
    "البريد الإلكتروني": "Email Address",
    "كلمة المرور": "Password",
    "الاسم الكامل": "Full Name",
    "اكتب اسمك الكامل": "Enter your full name",
    "أدخل بريدك الإلكتروني": "Enter your email address",
    "أدخل كلمة المرور": "Enter your password",
    "أدخل كلمة مرور قوية": "Enter a strong password",
    "إظهار": "Show",
    "لديك حساب بالفعل؟": "Already have an account?",
    "ليس لديك حساب؟": "Do not have an account?",
    "نسيت كلمة المرور؟": "Forgot password?",
    "فتح البوت": "Open Bot",
    "تأكد من البوت الرسمي": "Verify the official bot",
    "تأكيد البوت": "Verify Bot",
    "تفعيل الحساب": "Verify Account",
    "كود التفعيل": "Verification Code",
    "تفعيل الآن": "Verify Now",
    "تم إنشاء الحساب": "Account Created",
    "حسابك جاهز للانطلاق": "Your account is ready",
    "الدفع": "Payment",
    "الدفع اليدوي": "Manual Payment",
    "سجل الفواتير": "Invoice History",
    "الدليل": "Guide",
    "المدفوعات": "Payments",
    "المستخدمين": "Users",
    "المستخدمون": "Users",
    "الإشارات": "Signals",
    "الإيرادات": "Revenue",
    "الخطة": "Plan",
    "الحالة": "Status",
    "تحديث": "Update",
    "حفظ": "Save",
    "إرسال": "Send",
    "إلغاء": "Cancel",
    "رجوع": "Back",
    "التالي": "Next",
    "السابق": "Previous",
    "تواصل معنا": "Contact",
    "من نحن": "About",
    "مركز الدعم": "Support Center",
    "التوثيق": "Documentation",
    "سياسة الخصوصية": "Privacy Policy",
    "الشروط": "Terms",
    "سياسة الاسترداد": "Refund Policy",
    "إخلاء مسؤولية المخاطر": "Risk Disclaimer",
    "سياسة الكوكيز": "Cookie Policy",
    "حسابك مربوط بالبوت": "Your account is linked to the bot",
    "حسابك غير مربوط بالبوت": "Your account is not linked to the bot",
    "افتح البوت الرسمي واتبع رابط الربط الآمن، ثم سجل دخولك من الموقع لتأكيد الحساب.": "Open the official bot, follow the secure linking link, then log in from the website to confirm your account.",
    "مش بتوصلك Signals؟": "Not receiving signals?",
    "بعد الدخول يمكنك تفعيل الخطة، مراجعة الفواتير، وربط تيليجرام بأمان.": "After login you can activate your plan, review invoices, and link Telegram securely.",
    "مرحبًا بعودتك، ادخل لحسابك وربط البوت بسهولة.": "Welcome back. Log in to your account and link the bot easily.",
    "ابدأ رحلتك الاحترافية": "Start your professional journey",
    "مع Nexora AI Trader": "with Nexora AI Trader",
    "انضم إلى المتداولين الذين يستخدمون تحليلًا مدعومًا بالذكاء الاصطناعي، إدارة مخاطر، وتسليم إشارات عبر تيليجرام.": "Join traders using AI-assisted analysis, risk management, and Telegram signal delivery."
  };

  const enBase = {
    "Home": "Home",
    "Features": "Features",
    "Pricing": "Pricing",
    "Proof": "Proof",
    "Dashboard": "Dashboard",
    "Login": "Login",
    "Logout": "Logout",
    "Register": "Register",
    "Get Started": "Get Started",
    "Start Free Trial": "Start Free Trial",
    "Watch Demo": "Watch Demo",
    "View Plans": "View Plans",
    "Connect Telegram": "Connect Telegram",
    "Bot Check": "Bot Check",
    "Manual Payment": "Manual Payment",
    "Payment": "Payment",
    "Payments": "Payments",
    "Invoices": "Invoices",
    "Profile": "Profile",
    "Settings": "Settings",
    "Support": "Support",
    "Support Center": "Support Center",
    "Contact Support": "Contact Support",
    "Current Plan": "Current Plan",
    "Plan Status": "Plan Status",
    "Subscription Status": "Subscription Status",
    "Remaining Days": "Remaining Days",
    "Telegram Status": "Telegram Status",
    "Connected": "Connected",
    "Not Connected": "Not Connected",
    "Active": "Active",
    "Inactive": "Inactive",
    "Free Trial": "Free Trial",
    "Basic": "Basic",
    "Pro": "Pro",
    "Elite": "Elite",
    "Pro 2 Years": "Pro 2 Years",
    "Upgrade": "Upgrade",
    "Upgrade Plan": "Upgrade Plan",
    "Signals": "Signals",
    "Recent Signals": "Recent Signals",
    "Live Signals": "Live Signals",
    "Get New Signals": "Get New Signals",
    "Auto Trading": "Auto Trading",
    "Risk Protection": "Risk Protection",
    "Signal Quality": "Signal Quality",
    "Confidence": "Confidence",
    "Win Rate": "Win Rate",
    "Total Signals": "Total Signals",
    "Open Trades": "Open Trades",
    "Closed Trades": "Closed Trades",
    "Performance": "Performance",
    "AI Analysis": "AI Analysis",
    "Referral": "Referral",
    "Referrals": "Referrals",
    "Invite & Earn": "Invite & Earn",
    "Referral Link": "Referral Link",
    "Copy": "Copy",
    "Copied": "Copied",
    "Free Earn": "Free Earn",
    "Watch Video & Unlock": "Watch Video & Unlock",
    "Upgrade: No Ads": "Upgrade: No Ads",
    "Admin Overview": "Admin Overview",
    "Users": "Users",
    "Subscriptions": "Subscriptions",
    "Revenue": "Revenue",
    "System Health": "System Health",
    "Maintenance": "Maintenance",
    "Search users": "Search users",
    "Actions": "Actions",
    "Email Address": "Email Address",
    "Password": "Password",
    "Full Name": "Full Name",
    "Forgot password?": "Forgot password?",
    "Create Account": "Create Account",
    "Already have an account?": "Already have an account?",
    "Open Bot": "Open Bot",
    "Verify Bot": "Verify Bot",
    "Verify the official bot": "Verify the official bot",
    "Save": "Save",
    "Cancel": "Cancel",
    "Back": "Back",
    "Next": "Next",
    "Send": "Send",
    "Language": "Language",
    "AI crypto signal platform for serious traders": "AI crypto signal platform for serious traders",
    "Curated Signals": "Curated Signals",
    "Complete Dashboard": "Complete Dashboard",
    "Telegram Linking": "Telegram Linking",
    "Manual and Automatic Payments": "Manual and Automatic Payments",
    "How the system thinks": "How the system thinks",
    "Try the System": "Try the System",
    "Clear plans without friction": "Clear plans without friction",
    "Frequently asked questions": "Frequently asked questions",
    "Does the bot guarantee profit?": "Does the bot guarantee profit?",
    "Do I need experience?": "Do I need experience?",
    "Can the bot withdraw my funds?": "Can the bot withdraw my funds?",
    "How do I verify the bot?": "How do I verify the bot?",
    "Is manual payment available?": "Is manual payment available?",
    "What happens after registration?": "What happens after registration?",
    "Important Links": "Important Links",
    "Sections": "Sections",
    "Your account is linked to the bot": "Your account is linked to the bot",
    "Your account is not linked to the bot": "Your account is not linked to the bot",
    "Open the official bot, follow the secure linking link, then log in from the website to confirm your account.": "Open the official bot, follow the secure linking link, then log in from the website to confirm your account.",
    "Not receiving signals?": "Not receiving signals?",
    "After login you can activate your plan, review invoices, and link Telegram securely.": "After login you can activate your plan, review invoices, and link Telegram securely.",
    "Welcome back. Log in to your account and link the bot easily.": "Welcome back. Log in to your account and link the bot easily.",
    "Start your professional journey": "Start your professional journey",
    "with Nexora AI Trader": "with Nexora AI Trader",
    "Join traders using AI-assisted analysis, risk management, and Telegram signal delivery.": "Join traders using AI-assisted analysis, risk management, and Telegram signal delivery."
  };

  const translations = {
    en: Object.assign({}, arToEn),
    ar: {
      "Home": "الرئيسية",
      "Features": "المميزات",
      "Pricing": "الأسعار",
      "Proof": "الإثباتات",
      "Dashboard": "لوحة التحكم",
      "Login": "تسجيل الدخول",
      "Logout": "تسجيل الخروج",
      "Register": "إنشاء حساب",
      "Get Started": "ابدأ الآن",
      "Start Free Trial": "ابدأ التجربة المجانية",
      "Watch Demo": "شاهد العرض",
      "View Plans": "عرض الخطط",
      "Connect Telegram": "ربط تيليجرام",
      "Bot Check": "فحص البوت",
      "Manual Payment": "الدفع اليدوي",
      "Payment": "الدفع",
      "Payments": "المدفوعات",
      "Invoices": "الفواتير",
      "Profile": "الملف الشخصي",
      "Settings": "الإعدادات",
      "Support": "الدعم",
      "Support Center": "مركز الدعم",
      "Contact Support": "تواصل مع الدعم",
      "Current Plan": "الخطة الحالية",
      "Plan Status": "حالة الخطة",
      "Subscription Status": "حالة الاشتراك",
      "Remaining Days": "الأيام المتبقية",
      "Telegram Status": "حالة تيليجرام",
      "Connected": "متصل",
      "Not Connected": "غير متصل",
      "Active": "نشط",
      "Inactive": "غير نشط",
      "Free Trial": "تجربة مجانية",
      "Basic": "أساسي",
      "Pro": "احترافي",
      "Elite": "نخبة",
      "Pro 2 Years": "برو سنتين",
      "Upgrade": "ترقية",
      "Upgrade Plan": "ترقية الخطة",
      "Signals": "الإشارات",
      "Recent Signals": "آخر الإشارات",
      "Live Signals": "الإشارات المباشرة",
      "Get New Signals": "احصل على إشارات جديدة",
      "Auto Trading": "التداول التلقائي",
      "Risk Protection": "حماية المخاطر",
      "Signal Quality": "جودة الإشارة",
      "Confidence": "الثقة",
      "Win Rate": "نسبة النجاح",
      "Total Signals": "إجمالي الإشارات",
      "Open Trades": "الصفقات المفتوحة",
      "Closed Trades": "الصفقات المغلقة",
      "Performance": "الأداء",
      "AI Analysis": "تحليل الذكاء الاصطناعي",
      "Referral": "الإحالة",
      "Referrals": "الإحالات",
      "Invite & Earn": "ادع واربح",
      "Referral Link": "رابط الإحالة",
      "Copy": "نسخ",
      "Copied": "تم النسخ",
      "Free Earn": "اربح مجانًا",
      "Watch Video & Unlock": "شاهد الفيديو وافتح الإشارة",
      "Upgrade: No Ads": "ترقية بدون إعلانات",
      "Admin Overview": "نظرة عامة للأدمن",
      "Users": "المستخدمون",
      "Subscriptions": "الاشتراكات",
      "Revenue": "الإيرادات",
      "System Health": "صحة النظام",
      "Maintenance": "الصيانة",
      "Search users": "البحث عن المستخدمين",
      "Actions": "الإجراءات",
      "Email Address": "البريد الإلكتروني",
      "Password": "كلمة المرور",
      "Full Name": "الاسم الكامل",
      "Forgot password?": "نسيت كلمة المرور؟",
      "Create Account": "إنشاء حساب",
      "Already have an account?": "لديك حساب بالفعل؟",
      "Open Bot": "فتح البوت",
      "Verify Bot": "تأكيد البوت",
      "Verify the official bot": "تأكد من البوت الرسمي",
      "Save": "حفظ",
      "Cancel": "إلغاء",
      "Back": "رجوع",
      "Next": "التالي",
      "Send": "إرسال",
      "Language": "اللغة",
      "AI crypto signal platform for serious traders": "منصة إشارات كريبتو ذكية للمتداول الجاد",
      "Curated Signals": "إشارات منتقاة",
      "Complete Dashboard": "لوحة تحكم كاملة",
      "Telegram Linking": "ربط تيليجرام",
      "Manual and Automatic Payments": "دفع يدوي وأوتوماتيك",
      "How the system thinks": "كيف يفكر النظام؟",
      "Try the System": "اختبر النظام",
      "Clear plans without friction": "خطط واضحة بدون تعقيد",
      "Frequently asked questions": "أسئلة شائعة قبل الاشتراك",
      "Does the bot guarantee profit?": "هل يضمن البوت الربح؟",
      "Do I need experience?": "هل أحتاج خبرة؟",
      "Can the bot withdraw my funds?": "هل يمكن للبوت سحب أموالي؟",
      "How do I verify the bot?": "كيف أتأكد من البوت؟",
      "Is manual payment available?": "هل يوجد دفع يدوي؟",
      "What happens after registration?": "ماذا يحدث بعد التسجيل؟",
      "Important Links": "روابط مهمة",
      "Sections": "الأقسام",
      "Your account is linked to the bot": "حسابك مربوط بالبوت",
      "Your account is not linked to the bot": "حسابك غير مربوط بالبوت",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm your account.": "افتح البوت الرسمي واتبع رابط الربط الآمن، ثم سجل دخولك من الموقع لتأكيد الحساب.",
      "Not receiving signals?": "مش بتوصلك Signals؟",
      "After login you can activate your plan, review invoices, and link Telegram securely.": "بعد الدخول يمكنك تفعيل الخطة، مراجعة الفواتير، وربط تيليجرام بأمان.",
      "Welcome back. Log in to your account and link the bot easily.": "مرحبًا بعودتك، ادخل لحسابك وربط البوت بسهولة.",
      "Start your professional journey": "ابدأ رحلتك الاحترافية",
      "with Nexora AI Trader": "مع Nexora AI Trader",
      "Join traders using AI-assisted analysis, risk management, and Telegram signal delivery.": "انضم إلى المتداولين الذين يستخدمون تحليلًا مدعومًا بالذكاء الاصطناعي، إدارة مخاطر، وتسليم إشارات عبر تيليجرام."
    },
    es: {
      "Home": "Inicio", "Features": "Funciones", "Pricing": "Precios", "Proof": "Pruebas", "Dashboard": "Panel", "Login": "Iniciar sesión", "Logout": "Salir", "Register": "Registro", "Get Started": "Empezar", "Start Free Trial": "Prueba gratis", "Watch Demo": "Ver demo", "View Plans": "Ver planes", "Connect Telegram": "Conectar Telegram", "Bot Check": "Verificar bot", "Manual Payment": "Pago manual", "Payment": "Pago", "Payments": "Pagos", "Invoices": "Facturas", "Profile": "Perfil", "Settings": "Ajustes", "Support": "Soporte", "Current Plan": "Plan actual", "Subscription Status": "Estado de suscripción", "Remaining Days": "Días restantes", "Telegram Status": "Estado de Telegram", "Connected": "Conectado", "Not Connected": "No conectado", "Active": "Activo", "Signals": "Señales", "Recent Signals": "Señales recientes", "Auto Trading": "Trading automático", "Risk Protection": "Protección de riesgo", "Confidence": "Confianza", "Win Rate": "Tasa de acierto", "Performance": "Rendimiento", "AI Analysis": "Análisis de IA", "Email Address": "Correo electrónico", "Password": "Contraseña", "Full Name": "Nombre completo", "Create Account": "Crear cuenta", "Open Bot": "Abrir bot", "Language": "Idioma"
    },
    fr: {
      "Home": "Accueil", "Features": "Fonctionnalités", "Pricing": "Tarifs", "Proof": "Preuves", "Dashboard": "Tableau de bord", "Login": "Connexion", "Logout": "Déconnexion", "Register": "Inscription", "Get Started": "Commencer", "Start Free Trial": "Essai gratuit", "Watch Demo": "Voir la démo", "View Plans": "Voir les plans", "Connect Telegram": "Connecter Telegram", "Bot Check": "Vérifier le bot", "Payment": "Paiement", "Payments": "Paiements", "Invoices": "Factures", "Profile": "Profil", "Settings": "Paramètres", "Support": "Support", "Current Plan": "Plan actuel", "Subscription Status": "Statut d'abonnement", "Remaining Days": "Jours restants", "Telegram Status": "Statut Telegram", "Connected": "Connecté", "Not Connected": "Non connecté", "Active": "Actif", "Signals": "Signaux", "Recent Signals": "Signaux récents", "Auto Trading": "Trading automatique", "Risk Protection": "Protection du risque", "Confidence": "Confiance", "Win Rate": "Taux de réussite", "Performance": "Performance", "AI Analysis": "Analyse IA", "Language": "Langue"
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

  function normalizeLanguage(value) {
    const code = String(value || "en").split("-")[0].toLowerCase();
    return languages.some((item) => item.code === code) ? code : "en";
  }

  function activeLanguage() {
    return languages.find((item) => item.code === current) || languages[0];
  }

  function switchUrl(code) {
    const next = window.location.pathname + window.location.search;
    return "/set-language/" + encodeURIComponent(code) + "?next=" + encodeURIComponent(next);
  }

  function htmlEscape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function enhanceLanguageSwitchers() {
    document.querySelectorAll(".language-switcher").forEach((host) => {
      if (host.dataset.nexoraMultiLang === "ready") return;
      const active = activeLanguage();
      host.dataset.nexoraMultiLang = "ready";
      host.classList.add("nx-language-menu");
      host.innerHTML = [
        '<button class="nx-language-current" type="button" aria-haspopup="true" aria-expanded="false">',
        '<span class="nx-language-globe">🌐</span>',
        '<span class="nx-language-code">' + htmlEscape(active.code.toUpperCase()) + '</span>',
        '<span class="nx-language-name">' + htmlEscape(active.native) + '</span>',
        '<span class="nx-language-caret">⌄</span>',
        '</button>',
        '<div class="nx-language-list" role="menu">',
        languages.map((lang) => (
          '<a role="menuitem" class="' + (lang.code === current ? 'active' : '') + '" href="' + switchUrl(lang.code) + '">' +
          '<span class="nx-language-code">' + htmlEscape(lang.code.toUpperCase()) + '</span>' +
          '<span><strong>' + htmlEscape(lang.native) + '</strong><small>' + htmlEscape(lang.name) + '</small></span>' +
          '</a>'
        )).join(""),
        '</div>'
      ].join("");
    });
  }

  function buildMap() {
    if (current === "en") return translations.en;
    const target = translations[current] || {};
    if (current === "ar") return target;

    const bridge = {};
    Object.entries(arToEn).forEach(([arabicText, englishText]) => {
      if (target[englishText]) bridge[arabicText] = target[englishText];
    });
    return Object.assign({}, target, bridge);
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
    const map = buildMap();
    if (!Object.keys(map).length) return;
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
    document.querySelectorAll("[placeholder], [alt], [title], [aria-label], input[type='submit'], input[type='button']").forEach((el) => {
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
    const trigger = event.target.closest(".nx-language-current");
    document.querySelectorAll(".nx-language-menu.open").forEach((menu) => {
      if (!trigger || !menu.contains(trigger)) menu.classList.remove("open");
    });
    if (trigger) {
      const menu = trigger.closest(".nx-language-menu");
      menu.classList.toggle("open");
      trigger.setAttribute("aria-expanded", menu.classList.contains("open") ? "true" : "false");
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    enhanceLanguageSwitchers();
    translatePage();
  });

  window.NexoraI18n = {
    languages,
    current,
    translatePage,
    translateText
  };
})();

// === NEXORA V3 ULTIMATE UI BOOT ===
(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function pageKind() {
    const path = window.location.pathname || "/";
    if (path.includes("admin")) return "nx-admin";
    if (path.includes("dashboard")) return "nx-dashboard";
    if (path.includes("login") || path.includes("register") || path.includes("forgot") || path.includes("reset")) return "nx-auth";
    if (path.includes("payment") || path.includes("invoice")) return "nx-payment";
    if (path.includes("proof")) return "nx-proof";
    if (path.includes("health")) return "nx-health";
    return "nx-site";
  }

  function ensureFloatingThemeButton() {
    if (document.querySelector(".theme-toggle, .nx-floating-theme")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nx-floating-theme theme-toggle";
    button.setAttribute("aria-label", "Toggle theme");
    button.innerHTML = '<span>☀</span><span>◐</span>';
    document.body.appendChild(button);
  }

  function addAmbientOrbs() {
    if (document.querySelector(".nx-v3-orb")) return;
    ["one", "two", "three"].forEach((name) => {
      const orb = document.createElement("span");
      orb.className = "nx-v3-orb nx-v3-orb-" + name;
      orb.setAttribute("aria-hidden", "true");
      document.body.appendChild(orb);
    });
  }

  function initMarketPreview() {
    const cards = document.querySelectorAll("[data-market-symbol]");
    if (!cards.length) return;

    const fallback = {
      BTCUSDT: { price: "68,539.24", change: "+1.24" },
      ETHUSDT: { price: "3,728.41", change: "+2.15" },
      BNBUSDT: { price: "604.89", change: "+1.03" },
      SOLUSDT: { price: "152.63", change: "+3.42" },
      XRPUSDT: { price: "0.4792", change: "+1.87" },
      DOGEUSDT: { price: "0.1234", change: "+2.94" }
    };

    function render(symbol, data) {
      document.querySelectorAll('[data-market-symbol="' + symbol + '"]').forEach((card) => {
        const price = card.querySelector("[data-market-price]");
        const change = card.querySelector("[data-market-change]");
        if (price && data.price) price.textContent = data.price;
        if (change && data.change) {
          const numeric = Number(String(data.change).replace("%", ""));
          change.textContent = (numeric > 0 ? "+" : "") + numeric.toFixed(2) + "%";
          change.classList.toggle("negative", numeric < 0);
          change.classList.toggle("positive", numeric >= 0);
        }
      });
    }

    Object.keys(fallback).forEach((symbol) => render(symbol, fallback[symbol]));

    async function refresh() {
      const symbols = Array.from(new Set(Array.from(cards).map((card) => card.dataset.marketSymbol).filter(Boolean)));
      await Promise.all(symbols.map(async (symbol) => {
        try {
          const response = await fetch("https://api.binance.us/api/v3/ticker/24hr?symbol=" + encodeURIComponent(symbol), { cache: "no-store" });
          if (!response.ok) return;
          const data = await response.json();
          render(symbol, {
            price: Number(data.lastPrice).toLocaleString(undefined, { maximumFractionDigits: Number(data.lastPrice) > 10 ? 2 : 4 }),
            change: data.priceChangePercent
          });
        } catch (error) {
          // Keep fallback values if public market data is unavailable.
        }
      }));
    }

    refresh();
    window.setInterval(refresh, 45000);
  }

  function initTradingViewPreview() {
    // The landing page now owns the professional full-width terminal.
    // Remove any legacy mini preview that old cached markup may inject.
    document.querySelectorAll(".nx-tv-wrap.is-legacy, .nx-tradingview-preview").forEach((node) => node.remove());
  }

  ready(() => {
    document.body.classList.add("nx-v3-ui", pageKind());
    ensureFloatingThemeButton();
    addAmbientOrbs();
    initMarketPreview();
    initTradingViewPreview();
  });
})();
