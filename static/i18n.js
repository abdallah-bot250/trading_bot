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

  const dashboardCopy = {
    ar: {
      "Telegram is not linked": "تيليجرام غير مربوط",
      "To receive free or paid signals, complete one secure step:": "لاستقبال الإشارات المجانية أو المدفوعة، أكمل خطوة آمنة واحدة:",
      "Open the bot": "افتح البوت",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "افتح البوت الرسمي، واتبع رابط الربط الآمن، ثم سجل الدخول من الموقع لتأكيد تيليجرام.",
      "Without this step, signals will not reach you.": "بدون هذه الخطوة لن تصلك الإشارات.",
      "Open Bot Now": "افتح البوت الآن",
      "Telegram is linked": "تيليجرام مربوط",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "ممتاز — ستصلك الإشارات على تيليجرام حسب باقتك وحالة السوق.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "إذا كان البوت يعمل والفرصة قوية، ستصلك مباشرة.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "البوت لا يرسل صفقات عشوائية — يتم الإرسال فقط عند وجود فرصة واضحة وقوية.",
      "User Guide": "دليل الاستخدام",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "اربح من مشاركة البوت — كل اشتراك جديد من رابطك يتم احتسابه لك.",
      "Your referral link:": "رابط الإحالة الخاص بك:",
      "Commission Withdrawal Request": "طلب سحب العمولة",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "الحد الأدنى: $25 | الحد الأقصى: $300 | خلال 24 ساعة",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "تحكم في استقبال الإشارات أو تنفيذ التداول التلقائي حسب باقتك وإعداداتك الحالية.",
      "Pause Bot": "إيقاف البوت",
      "Start Bot": "تشغيل البوت",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "البوت يعمل الآن وسيرسل الصفقات تلقائيًا حسب حالة السوق وباقتك.",
      "The bot is paused — start it to receive signals or run auto-trading.": "البوت متوقف حاليًا — شغّله لاستقبال الإشارات أو تشغيل التداول التلقائي.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "تحكم في أنواع الإشارات التي يستقبلها حسابك. المحرك يقيّم Spot و Futures بشكل مستقل ويختار أفضل الفرص حسب الجودة.",
      "Enable or disable Spot opportunities": "تفعيل أو إيقاف فرص Spot",
      "Enable or disable Futures opportunities": "تفعيل أو إيقاف فرص Futures",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "اربط الـ API واضبط إعدادات التداول — البوت لا يستطيع السحب أو الإيداع، فقط تنفيذ الصفقات.",
      "API Connection": "ربط API",
      "Trading Settings": "إعدادات التداول",
      "Receive Spot opportunities when quality is suitable": "استقبال فرص Spot عند جودة مناسبة",
      "Receive Futures opportunities when quality is suitable": "استقبال فرص Futures عند جودة مناسبة",
      "Everything in Basic +": "كل مميزات Basic +",
      "Everything in Pro +": "كل مميزات Pro +",
      "Results shown here are linked to your account and current trading data.": "النتائج المعروضة هنا مرتبطة بحسابك وبيانات تداولك الحالية.",
      "Profit performance updates automatically.": "أداء الأرباح يتم تحديثه تلقائيًا.",
      "Referral link copied": "تم نسخ رابط الإحالة"
    },
    es: {
      "Telegram is not linked": "Telegram no está vinculado",
      "To receive free or paid signals, complete one secure step:": "Para recibir señales gratuitas o de pago, completa un paso seguro:",
      "Open the bot": "Abrir el bot",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Abre el bot oficial, sigue el enlace seguro y luego inicia sesión en el sitio para confirmar Telegram.",
      "Without this step, signals will not reach you.": "Sin este paso, no recibirás las señales.",
      "Open Bot Now": "Abrir bot ahora",
      "Telegram is linked": "Telegram está vinculado",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Perfecto: recibirás señales en Telegram según tu plan y las condiciones del mercado.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Si el bot está activo y la oportunidad es fuerte, la recibirás directamente.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "El bot no envía operaciones aleatorias; solo entrega señales cuando existe una oportunidad clara y fuerte.",
      "User Guide": "Guía de uso",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Gana compartiendo el bot: cada nueva suscripción desde tu enlace queda registrada para ti.",
      "Your referral link:": "Tu enlace de referido:",
      "Commission Withdrawal Request": "Solicitud de retiro de comisión",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Mínimo: $25 | Máximo: $300 | en 24 horas",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Controla la entrega de señales o la ejecución automática según tu plan y configuración actual.",
      "Pause Bot": "Pausar bot",
      "Start Bot": "Iniciar bot",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "El bot está activo y enviará operaciones automáticamente según el mercado y tu plan.",
      "The bot is paused — start it to receive signals or run auto-trading.": "El bot está pausado; actívalo para recibir señales o ejecutar auto-trading.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Controla los tipos de señales que recibe tu cuenta. El motor evalúa Spot y Futures por separado y elige las mejores oportunidades por calidad.",
      "Enable or disable Spot opportunities": "Activar o desactivar oportunidades Spot",
      "Enable or disable Futures opportunities": "Activar o desactivar oportunidades Futures",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Conecta tu API y configura el trading; el bot no puede retirar ni depositar, solo ejecutar operaciones.",
      "API Connection": "Conexión API",
      "Trading Settings": "Configuración de trading",
      "Receive Spot opportunities when quality is suitable": "Recibir oportunidades Spot cuando la calidad sea adecuada",
      "Receive Futures opportunities when quality is suitable": "Recibir oportunidades Futures cuando la calidad sea adecuada",
      "Everything in Basic +": "Todo en Basic +",
      "Everything in Pro +": "Todo en Pro +",
      "Results shown here are linked to your account and current trading data.": "Los resultados mostrados aquí están vinculados a tu cuenta y datos de trading actuales.",
      "Profit performance updates automatically.": "El rendimiento de ganancias se actualiza automáticamente.",
      "Referral link copied": "Enlace de referido copiado"
    },
    fr: {
      "Telegram is not linked": "Telegram n'est pas lié",
      "To receive free or paid signals, complete one secure step:": "Pour recevoir les signaux gratuits ou payants, complétez une étape sécurisée :",
      "Open the bot": "Ouvrir le bot",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Ouvrez le bot officiel, suivez le lien sécurisé, puis connectez-vous au site pour confirmer Telegram.",
      "Without this step, signals will not reach you.": "Sans cette étape, les signaux ne vous parviendront pas.",
      "Open Bot Now": "Ouvrir le bot maintenant",
      "Telegram is linked": "Telegram est lié",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Parfait — les signaux arriveront sur Telegram selon votre plan et les conditions du marché.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Si le bot est actif et que l'opportunité est forte, vous la recevrez directement.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Le bot n'envoie pas de trades aléatoires — l'envoi se fait uniquement lorsqu'une opportunité claire et forte existe.",
      "User Guide": "Guide utilisateur",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Gagnez en partageant le bot — chaque nouvel abonnement via votre lien est suivi pour vous.",
      "Your referral link:": "Votre lien de parrainage :",
      "Commission Withdrawal Request": "Demande de retrait de commission",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Minimum : 25 $ | Maximum : 300 $ | sous 24 heures",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Contrôlez l'envoi des signaux ou l'exécution auto-trading selon votre plan et vos paramètres.",
      "Pause Bot": "Mettre le bot en pause",
      "Start Bot": "Démarrer le bot",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Le bot est actif et enverra les trades automatiquement selon le marché et votre plan.",
      "The bot is paused — start it to receive signals or run auto-trading.": "Le bot est en pause — démarrez-le pour recevoir les signaux ou lancer l'auto-trading.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Contrôlez les types de signaux reçus. Le moteur évalue Spot et Futures séparément et choisit les meilleures opportunités selon la qualité.",
      "Enable or disable Spot opportunities": "Activer ou désactiver les opportunités Spot",
      "Enable or disable Futures opportunities": "Activer ou désactiver les opportunités Futures",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Connectez votre API et configurez le trading — le bot ne peut ni retirer ni déposer, seulement exécuter des trades.",
      "API Connection": "Connexion API",
      "Trading Settings": "Paramètres de trading",
      "Receive Spot opportunities when quality is suitable": "Recevoir les opportunités Spot lorsque la qualité est adaptée",
      "Receive Futures opportunities when quality is suitable": "Recevoir les opportunités Futures lorsque la qualité est adaptée",
      "Everything in Basic +": "Tout dans Basic +",
      "Everything in Pro +": "Tout dans Pro +",
      "Results shown here are linked to your account and current trading data.": "Les résultats affichés sont liés à votre compte et aux données de trading actuelles.",
      "Profit performance updates automatically.": "La performance des profits se met à jour automatiquement.",
      "Referral link copied": "Lien de parrainage copié"
    },
    de: {
      "Telegram is not linked": "Telegram ist nicht verbunden",
      "To receive free or paid signals, complete one secure step:": "Um kostenlose oder bezahlte Signale zu erhalten, schließen Sie einen sicheren Schritt ab:",
      "Open the bot": "Bot öffnen",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Öffnen Sie den offiziellen Bot, folgen Sie dem sicheren Link und melden Sie sich auf der Website an, um Telegram zu bestätigen.",
      "Without this step, signals will not reach you.": "Ohne diesen Schritt erreichen Sie keine Signale.",
      "Open Bot Now": "Bot jetzt öffnen",
      "Telegram is linked": "Telegram ist verbunden",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Sehr gut — Signale erreichen Sie auf Telegram gemäß Ihrem Plan und den Marktbedingungen.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Wenn der Bot aktiv ist und die Gelegenheit stark ist, erhalten Sie sie direkt.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Der Bot sendet keine zufälligen Trades — Signale werden nur bei klaren, starken Chancen gesendet.",
      "User Guide": "Benutzerhandbuch",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Verdienen Sie durch das Teilen des Bots — jede neue Anmeldung über Ihren Link wird erfasst.",
      "Your referral link:": "Ihr Empfehlungslink:",
      "Commission Withdrawal Request": "Provisionsauszahlung anfordern",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Minimum: 25 $ | Maximum: 300 $ | innerhalb von 24 Stunden",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Steuern Sie Signale oder Auto-Trading gemäß Plan und aktuellen Einstellungen.",
      "Pause Bot": "Bot pausieren",
      "Start Bot": "Bot starten",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Der Bot ist aktiv und sendet Trades automatisch basierend auf Marktbedingungen und Ihrem Plan.",
      "The bot is paused — start it to receive signals or run auto-trading.": "Der Bot ist pausiert — starten Sie ihn, um Signale zu erhalten oder Auto-Trading auszuführen.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Steuern Sie die Signaltypen Ihres Kontos. Die Engine bewertet Spot und Futures getrennt und wählt die besten Chancen nach Qualität.",
      "Enable or disable Spot opportunities": "Spot-Chancen aktivieren oder deaktivieren",
      "Enable or disable Futures opportunities": "Futures-Chancen aktivieren oder deaktivieren",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Verbinden Sie Ihre API und konfigurieren Sie Trading — der Bot kann nicht abheben oder einzahlen, nur Trades ausführen.",
      "API Connection": "API-Verbindung",
      "Trading Settings": "Trading-Einstellungen",
      "Receive Spot opportunities when quality is suitable": "Spot-Chancen erhalten, wenn die Qualität passt",
      "Receive Futures opportunities when quality is suitable": "Futures-Chancen erhalten, wenn die Qualität passt",
      "Everything in Basic +": "Alles in Basic +",
      "Everything in Pro +": "Alles in Pro +",
      "Results shown here are linked to your account and current trading data.": "Die hier gezeigten Ergebnisse sind mit Ihrem Konto und aktuellen Trading-Daten verknüpft.",
      "Profit performance updates automatically.": "Die Gewinnentwicklung wird automatisch aktualisiert.",
      "Referral link copied": "Empfehlungslink kopiert"
    },
    tr: {
      "Telegram is not linked": "Telegram bağlı değil",
      "To receive free or paid signals, complete one secure step:": "Ücretsiz veya ücretli sinyalleri almak için tek güvenli adımı tamamlayın:",
      "Open the bot": "Botu aç",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Resmi botu açın, güvenli bağlantıyı takip edin, ardından Telegram'ı onaylamak için sitede giriş yapın.",
      "Without this step, signals will not reach you.": "Bu adım olmadan sinyaller size ulaşmaz.",
      "Open Bot Now": "Botu Şimdi Aç",
      "Telegram is linked": "Telegram bağlı",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Harika — sinyaller planınıza ve piyasa koşullarına göre Telegram'da size ulaşacak.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Bot aktifse ve fırsat güçlüyse doğrudan alırsınız.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Bot rastgele işlem göndermez — yalnızca net ve güçlü fırsat olduğunda gönderim yapar.",
      "User Guide": "Kullanım Kılavuzu",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Botu paylaşarak kazanın — bağlantınızdan gelen her yeni abonelik sizin için takip edilir.",
      "Your referral link:": "Referans bağlantınız:",
      "Commission Withdrawal Request": "Komisyon Çekim Talebi",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Minimum: $25 | Maksimum: $300 | 24 saat içinde",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Planınıza ve ayarlarınıza göre sinyal teslimini veya otomatik işlem yürütmeyi kontrol edin.",
      "Pause Bot": "Botu Durdur",
      "Start Bot": "Botu Başlat",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Bot aktif ve piyasa koşullarına ve planınıza göre işlemleri otomatik gönderecek.",
      "The bot is paused — start it to receive signals or run auto-trading.": "Bot duraklatıldı — sinyal almak veya otomatik işlem çalıştırmak için başlatın.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Hesabınızın aldığı sinyal türlerini kontrol edin. Motor Spot ve Futures'ı ayrı değerlendirir ve kaliteye göre en iyi fırsatları seçer.",
      "Enable or disable Spot opportunities": "Spot fırsatlarını aç veya kapat",
      "Enable or disable Futures opportunities": "Futures fırsatlarını aç veya kapat",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "API'nizi bağlayın ve işlem ayarlarını yapın — bot para çekemez veya yatıramaz, sadece işlem yürütür.",
      "API Connection": "API Bağlantısı",
      "Trading Settings": "İşlem Ayarları",
      "Receive Spot opportunities when quality is suitable": "Kalite uygunsa Spot fırsatlarını al",
      "Receive Futures opportunities when quality is suitable": "Kalite uygunsa Futures fırsatlarını al",
      "Everything in Basic +": "Basic içindeki her şey +",
      "Everything in Pro +": "Pro içindeki her şey +",
      "Results shown here are linked to your account and current trading data.": "Burada gösterilen sonuçlar hesabınız ve güncel işlem verilerinizle bağlantılıdır.",
      "Profit performance updates automatically.": "Kâr performansı otomatik güncellenir.",
      "Referral link copied": "Referans bağlantısı kopyalandı"
    },
    pt: {
      "Telegram is not linked": "Telegram não está conectado",
      "To receive free or paid signals, complete one secure step:": "Para receber sinais gratuitos ou pagos, conclua uma etapa segura:",
      "Open the bot": "Abrir o bot",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Abra o bot oficial, siga o link seguro e depois entre no site para confirmar o Telegram.",
      "Without this step, signals will not reach you.": "Sem esta etapa, os sinais não chegarão até você.",
      "Open Bot Now": "Abrir bot agora",
      "Telegram is linked": "Telegram conectado",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Ótimo — os sinais chegarão no Telegram conforme seu plano e as condições do mercado.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Se o bot estiver ativo e a oportunidade for forte, você a receberá diretamente.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "O bot não envia trades aleatórios — o envio ocorre apenas quando há uma oportunidade clara e forte.",
      "User Guide": "Guia do usuário",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Ganhe compartilhando o bot — cada nova assinatura pelo seu link é rastreada para você.",
      "Your referral link:": "Seu link de indicação:",
      "Commission Withdrawal Request": "Solicitação de saque de comissão",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Mínimo: $25 | Máximo: $300 | em até 24 horas",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Controle o envio de sinais ou a execução automática conforme seu plano e configurações.",
      "Pause Bot": "Pausar bot",
      "Start Bot": "Iniciar bot",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "O bot está ativo e enviará trades automaticamente conforme o mercado e seu plano.",
      "The bot is paused — start it to receive signals or run auto-trading.": "O bot está pausado — inicie para receber sinais ou executar auto-trading.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Controle os tipos de sinais que sua conta recebe. O motor avalia Spot e Futures separadamente e seleciona as melhores oportunidades por qualidade.",
      "Enable or disable Spot opportunities": "Ativar ou desativar oportunidades Spot",
      "Enable or disable Futures opportunities": "Ativar ou desativar oportunidades Futures",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Conecte sua API e configure o trading — o bot não pode sacar nem depositar, apenas executar trades.",
      "API Connection": "Conexão API",
      "Trading Settings": "Configurações de trading",
      "Receive Spot opportunities when quality is suitable": "Receber oportunidades Spot quando a qualidade for adequada",
      "Receive Futures opportunities when quality is suitable": "Receber oportunidades Futures quando a qualidade for adequada",
      "Everything in Basic +": "Tudo no Basic +",
      "Everything in Pro +": "Tudo no Pro +",
      "Results shown here are linked to your account and current trading data.": "Os resultados mostrados aqui estão ligados à sua conta e aos dados atuais de trading.",
      "Profit performance updates automatically.": "O desempenho de lucro é atualizado automaticamente.",
      "Referral link copied": "Link de indicação copiado"
    },
    ru: {
      "Telegram is not linked": "Telegram не подключен",
      "To receive free or paid signals, complete one secure step:": "Чтобы получать бесплатные или платные сигналы, выполните один безопасный шаг:",
      "Open the bot": "Открыть бота",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Откройте официального бота, перейдите по безопасной ссылке и войдите на сайт, чтобы подтвердить Telegram.",
      "Without this step, signals will not reach you.": "Без этого шага сигналы не будут приходить.",
      "Open Bot Now": "Открыть бота сейчас",
      "Telegram is linked": "Telegram подключен",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Отлично — сигналы будут приходить в Telegram согласно вашему плану и рыночным условиям.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Если бот активен и возможность сильная, вы получите её напрямую.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Бот не отправляет случайные сделки — отправка происходит только при ясной и сильной возможности.",
      "User Guide": "Руководство пользователя",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Зарабатывайте, делясь ботом — каждая новая подписка по вашей ссылке отслеживается.",
      "Your referral link:": "Ваша реферальная ссылка:",
      "Commission Withdrawal Request": "Запрос вывода комиссии",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Минимум: $25 | Максимум: $300 | в течение 24 часов",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Управляйте доставкой сигналов или автоторговлей согласно плану и настройкам.",
      "Pause Bot": "Приостановить бота",
      "Start Bot": "Запустить бота",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Бот активен и будет автоматически отправлять сделки согласно рынку и вашему плану.",
      "The bot is paused — start it to receive signals or run auto-trading.": "Бот остановлен — запустите его для получения сигналов или автоторговли.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Управляйте типами сигналов. Движок отдельно оценивает Spot и Futures и выбирает лучшие возможности по качеству.",
      "Enable or disable Spot opportunities": "Включить или выключить Spot-возможности",
      "Enable or disable Futures opportunities": "Включить или выключить Futures-возможности",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Подключите API и настройте торговлю — бот не может выводить или вносить средства, только выполнять сделки.",
      "API Connection": "API-подключение",
      "Trading Settings": "Настройки торговли",
      "Receive Spot opportunities when quality is suitable": "Получать Spot-возможности при подходящем качестве",
      "Receive Futures opportunities when quality is suitable": "Получать Futures-возможности при подходящем качестве",
      "Everything in Basic +": "Всё из Basic +",
      "Everything in Pro +": "Всё из Pro +",
      "Results shown here are linked to your account and current trading data.": "Показанные результаты связаны с вашим аккаунтом и текущими торговыми данными.",
      "Profit performance updates automatically.": "Динамика прибыли обновляется автоматически.",
      "Referral link copied": "Реферальная ссылка скопирована"
    },
    zh: {
      "Telegram is not linked": "Telegram 未连接",
      "To receive free or paid signals, complete one secure step:": "要接收免费或付费信号，请完成一个安全步骤：",
      "Open the bot": "打开机器人",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "打开官方机器人，使用安全链接，然后登录网站确认 Telegram。",
      "Without this step, signals will not reach you.": "没有这一步，你将无法收到信号。",
      "Open Bot Now": "立即打开机器人",
      "Telegram is linked": "Telegram 已连接",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "很好 — 信号会根据你的套餐和市场情况发送到 Telegram。",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "如果机器人已启用且机会足够强，你会直接收到。",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "机器人不会发送随机交易 — 只有出现清晰且强的机会时才会发送。",
      "User Guide": "用户指南",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "分享机器人即可赚取收益 — 通过你的链接产生的新订阅都会被记录。",
      "Your referral link:": "你的推荐链接：",
      "Commission Withdrawal Request": "佣金提现申请",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "最低：$25 | 最高：$300 | 24小时内",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "根据你的套餐和当前设置控制信号发送或自动交易执行。",
      "Pause Bot": "暂停机器人",
      "Start Bot": "启动机器人",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "机器人已启用，会根据市场情况和套餐自动发送交易。",
      "The bot is paused — start it to receive signals or run auto-trading.": "机器人已暂停 — 启动后可接收信号或运行自动交易。",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "控制账户接收的信号类型。系统会独立评估现货和合约，并按质量选择最佳机会。",
      "Enable or disable Spot opportunities": "启用或禁用现货机会",
      "Enable or disable Futures opportunities": "启用或禁用合约机会",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "连接 API 并配置交易设置 — 机器人不能提款或入金，只能执行交易。",
      "API Connection": "API 连接",
      "Trading Settings": "交易设置",
      "Receive Spot opportunities when quality is suitable": "质量合适时接收现货机会",
      "Receive Futures opportunities when quality is suitable": "质量合适时接收合约机会",
      "Everything in Basic +": "Basic 的全部功能 +",
      "Everything in Pro +": "Pro 的全部功能 +",
      "Results shown here are linked to your account and current trading data.": "此处显示的结果与你的账户和当前交易数据相关。",
      "Profit performance updates automatically.": "收益表现会自动更新。",
      "Referral link copied": "推荐链接已复制"
    },
    hi: {
      "Telegram is not linked": "Telegram लिंक नहीं है",
      "To receive free or paid signals, complete one secure step:": "मुफ्त या पेड सिग्नल पाने के लिए एक सुरक्षित कदम पूरा करें:",
      "Open the bot": "बॉट खोलें",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "आधिकारिक बॉट खोलें, सुरक्षित लिंक का पालन करें, फिर Telegram पुष्टि के लिए वेबसाइट से लॉगिन करें।",
      "Without this step, signals will not reach you.": "इस कदम के बिना सिग्नल आप तक नहीं पहुँचेंगे।",
      "Open Bot Now": "अभी बॉट खोलें",
      "Telegram is linked": "Telegram लिंक है",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "बढ़िया — आपके प्लान और बाजार स्थिति के अनुसार सिग्नल Telegram पर मिलेंगे।",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "यदि बॉट सक्रिय है और अवसर मजबूत है, तो आपको सीधे मिल जाएगा।",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "बॉट रैंडम ट्रेड नहीं भेजता — केवल स्पष्ट और मजबूत अवसर होने पर सिग्नल भेजता है।",
      "User Guide": "यूज़र गाइड",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "बॉट शेयर करके कमाएँ — आपके लिंक से हर नई सदस्यता ट्रैक होती है।",
      "Your referral link:": "आपका रेफरल लिंक:",
      "Commission Withdrawal Request": "कमीशन निकासी अनुरोध",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "न्यूनतम: $25 | अधिकतम: $300 | 24 घंटे में",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "अपने प्लान और सेटिंग्स के अनुसार सिग्नल डिलीवरी या ऑटो-ट्रेडिंग नियंत्रित करें।",
      "Pause Bot": "बॉट रोकें",
      "Start Bot": "बॉट शुरू करें",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "बॉट सक्रिय है और बाजार व आपके प्लान के अनुसार ट्रेड अपने आप भेजेगा।",
      "The bot is paused — start it to receive signals or run auto-trading.": "बॉट रुका है — सिग्नल पाने या ऑटो-ट्रेडिंग चलाने के लिए शुरू करें।",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "आपके खाते को मिलने वाले सिग्नल प्रकार नियंत्रित करें। इंजन Spot और Futures को अलग-अलग जांचता है और गुणवत्ता के आधार पर सर्वश्रेष्ठ अवसर चुनता है।",
      "Enable or disable Spot opportunities": "Spot अवसर चालू या बंद करें",
      "Enable or disable Futures opportunities": "Futures अवसर चालू या बंद करें",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "API जोड़ें और ट्रेडिंग सेटिंग्स करें — बॉट निकासी या जमा नहीं कर सकता, केवल ट्रेड निष्पादित करता है।",
      "API Connection": "API कनेक्शन",
      "Trading Settings": "ट्रेडिंग सेटिंग्स",
      "Receive Spot opportunities when quality is suitable": "गुणवत्ता सही होने पर Spot अवसर प्राप्त करें",
      "Receive Futures opportunities when quality is suitable": "गुणवत्ता सही होने पर Futures अवसर प्राप्त करें",
      "Everything in Basic +": "Basic की सभी चीजें +",
      "Everything in Pro +": "Pro की सभी चीजें +",
      "Results shown here are linked to your account and current trading data.": "यहाँ दिखाए गए परिणाम आपके खाते और वर्तमान ट्रेडिंग डेटा से जुड़े हैं।",
      "Profit performance updates automatically.": "लाभ प्रदर्शन अपने आप अपडेट होता है।",
      "Referral link copied": "रेफरल लिंक कॉपी हुआ"
    },
    ur: {
      "Telegram is not linked": "Telegram منسلک نہیں ہے",
      "To receive free or paid signals, complete one secure step:": "مفت یا paid سگنلز لینے کے لیے ایک محفوظ قدم مکمل کریں:",
      "Open the bot": "Bot کھولیں",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Official bot کھولیں، secure link follow کریں، پھر Telegram confirm کرنے کے لیے website سے login کریں۔",
      "Without this step, signals will not reach you.": "اس قدم کے بغیر signals آپ تک نہیں پہنچیں گے۔",
      "Open Bot Now": "Bot ابھی کھولیں",
      "Telegram is linked": "Telegram منسلک ہے",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "بہت اچھا — آپ کے plan اور market conditions کے مطابق signals Telegram پر پہنچیں گے۔",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "اگر bot active ہے اور opportunity strong ہے تو signal براہ راست ملے گا۔",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Bot random trades نہیں بھیجتا — صرف clear اور strong opportunity پر signal بھیجتا ہے۔",
      "User Guide": "User Guide",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Bot share کر کے earn کریں — آپ کے link سے ہر نئی subscription track ہوگی۔",
      "Your referral link:": "آپ کا referral link:",
      "Commission Withdrawal Request": "Commission withdrawal request",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Minimum: $25 | Maximum: $300 | 24 گھنٹے میں",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "اپنے plan اور settings کے مطابق signal delivery یا auto-trading execution control کریں۔",
      "Pause Bot": "Bot pause کریں",
      "Start Bot": "Bot start کریں",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Bot active ہے اور market conditions اور plan کے مطابق trades automatically بھیجے گا۔",
      "The bot is paused — start it to receive signals or run auto-trading.": "Bot paused ہے — signals لینے یا auto-trading چلانے کے لیے start کریں۔",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "اپنے account کے signal types control کریں۔ Engine Spot اور Futures کو الگ evaluate کر کے quality کے مطابق بہترین opportunities منتخب کرتا ہے۔",
      "Enable or disable Spot opportunities": "Spot opportunities enable یا disable کریں",
      "Enable or disable Futures opportunities": "Futures opportunities enable یا disable کریں",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "API connect کریں اور trading settings configure کریں — bot withdraw یا deposit نہیں کر سکتا، صرف trades execute کرتا ہے۔",
      "API Connection": "API Connection",
      "Trading Settings": "Trading Settings",
      "Receive Spot opportunities when quality is suitable": "Quality مناسب ہو تو Spot opportunities receive کریں",
      "Receive Futures opportunities when quality is suitable": "Quality مناسب ہو تو Futures opportunities receive کریں",
      "Everything in Basic +": "Basic کی تمام features +",
      "Everything in Pro +": "Pro کی تمام features +",
      "Results shown here are linked to your account and current trading data.": "یہاں دکھائے گئے results آپ کے account اور current trading data سے linked ہیں۔",
      "Profit performance updates automatically.": "Profit performance automatically update ہوتی ہے۔",
      "Referral link copied": "Referral link copy ہو گیا"
    },
    id: {
      "Telegram is not linked": "Telegram belum terhubung",
      "To receive free or paid signals, complete one secure step:": "Untuk menerima sinyal gratis atau berbayar, selesaikan satu langkah aman:",
      "Open the bot": "Buka bot",
      "Open the official bot, follow the secure linking link, then log in from the website to confirm Telegram.": "Buka bot resmi, ikuti tautan aman, lalu login dari website untuk mengonfirmasi Telegram.",
      "Without this step, signals will not reach you.": "Tanpa langkah ini, sinyal tidak akan sampai kepada Anda.",
      "Open Bot Now": "Buka Bot Sekarang",
      "Telegram is linked": "Telegram terhubung",
      "Great — signals will reach you on Telegram according to your plan and market conditions.": "Bagus — sinyal akan masuk ke Telegram sesuai paket dan kondisi pasar.",
      "If the bot is active and the opportunity is strong, you will receive it directly.": "Jika bot aktif dan peluang kuat, Anda akan menerimanya langsung.",
      "The bot does not send random trades — delivery happens only when a clear, strong opportunity exists.": "Bot tidak mengirim trade acak — pengiriman hanya terjadi saat ada peluang jelas dan kuat.",
      "User Guide": "Panduan Pengguna",
      "Earn by sharing the bot — every new subscription from your link is tracked for you.": "Dapatkan komisi dengan membagikan bot — setiap langganan baru dari tautan Anda akan dilacak.",
      "Your referral link:": "Tautan referral Anda:",
      "Commission Withdrawal Request": "Permintaan Penarikan Komisi",
      "Minimum: $25 | Maximum: $300 | within 24 hours": "Minimum: $25 | Maksimum: $300 | dalam 24 jam",
      "Control signal delivery or auto-trading execution based on your plan and current settings.": "Kontrol pengiriman sinyal atau eksekusi auto-trading berdasarkan paket dan pengaturan Anda.",
      "Pause Bot": "Jeda Bot",
      "Start Bot": "Mulai Bot",
      "The bot is active and will send trades automatically based on market conditions and your plan.": "Bot aktif dan akan mengirim trade otomatis berdasarkan kondisi pasar dan paket Anda.",
      "The bot is paused — start it to receive signals or run auto-trading.": "Bot dijeda — mulai untuk menerima sinyal atau menjalankan auto-trading.",
      "Control the signal types your account receives. The engine evaluates Spot and Futures independently and selects the best opportunities by quality.": "Kontrol jenis sinyal yang diterima akun Anda. Engine mengevaluasi Spot dan Futures secara terpisah dan memilih peluang terbaik berdasarkan kualitas.",
      "Enable or disable Spot opportunities": "Aktifkan atau nonaktifkan peluang Spot",
      "Enable or disable Futures opportunities": "Aktifkan atau nonaktifkan peluang Futures",
      "Connect your API and configure trading settings — the bot cannot withdraw or deposit, only execute trades.": "Hubungkan API dan konfigurasi trading — bot tidak bisa menarik atau deposit, hanya mengeksekusi trade.",
      "API Connection": "Koneksi API",
      "Trading Settings": "Pengaturan Trading",
      "Receive Spot opportunities when quality is suitable": "Terima peluang Spot saat kualitas sesuai",
      "Receive Futures opportunities when quality is suitable": "Terima peluang Futures saat kualitas sesuai",
      "Everything in Basic +": "Semua di Basic +",
      "Everything in Pro +": "Semua di Pro +",
      "Results shown here are linked to your account and current trading data.": "Hasil yang ditampilkan di sini terkait dengan akun dan data trading Anda saat ini.",
      "Profit performance updates automatically.": "Performa profit diperbarui otomatis.",
      "Referral link copied": "Tautan referral disalin"
    }
  };

  Object.keys(dashboardCopy).forEach((code) => {
    translations[code] = Object.assign(translations[code] || {}, dashboardCopy[code]);
  });

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
