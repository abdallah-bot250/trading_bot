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
