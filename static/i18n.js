(() => {
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
    ["بوت إشارات كريبتو ذكي للمتداول الجاد", "AI crypto signal platform for serious traders"],
    ["حوّل فوضى السوق إلى", "Turn market noise into"],
    ["قرارات أوضح", "clearer decisions"],
    ["قبل الدخول.", "before entry."],
    ["إشارات حسب نوع التداول", "Signals by trading type"],
    ["رفض الفرص الضعيفة", "Weak opportunities are filtered out"],
    ["تشغيل تلقائي اختياري", "Optional automated execution"],
    ["تجربة واضحة قبل الاشتراك", "A clear preview before subscribing"],
    ["كل ما يحتاجه المستخدم ليثق قبل الاشتراك", "Everything users need before subscribing"],
    ["إشارات منتقاة", "Curated Signals"],
    ["لوحة تحكم كاملة", "Complete Dashboard"],
    ["ربط تيليجرام", "Telegram Linking"],
    ["دفع يدوي وأوتوماتيك", "Manual and Automatic Payments"],
    ["تجربة مجانية", "Free Trial"],
    ["طبقة ذكاء اصطناعي فوق التحليل الفني", "An AI layer above technical analysis"],
    ["كيف يفكر النظام؟", "How the system thinks"],
    ["اختبر النظام", "Try the System"],
    ["خطط واضحة بدون تعقيد", "Clear plans without friction"],
    ["ابدأ Starter", "Start Starter"],
    ["ابدأ Pro", "Start Pro"],
    ["ابدأ Elite", "Start Elite"],
    ["إثباتات وتجارب من داخل النظام", "Proof and real platform experience"],
    ["وضوح الإشارة", "Clear Signals"],
    ["نتائج قابلة للمراجعة", "Reviewable Results"],
    ["ثقة قبل الدفع", "Trust Before Payment"],
    ["افتح صفحة الإثباتات", "Open Proof Page"],
    ["نظام إحالات يساعد المشروع يكبر", "Affiliate system built for growth"],
    ["مصمم للنمو", "Built for Growth"],
    ["ابدأ وشارك رابطك", "Start and Share Your Link"],
    ["الأمان جزء من المنتج، وليس إضافة جانبية", "Security is part of the product"],
    ["حماية للفورمات المهمة داخل الموقع.", "Protection for important site forms."],
    ["كوكيز آمنة و HttpOnly و SameSite.", "Secure HttpOnly SameSite cookies."],
    ["تسجيل أحداث حساسة لمراجعة الإدارة.", "Sensitive events are logged for admin review."],
    ["صفحة رسمية للتأكد من رابط البوت قبل الربط.", "Official page to verify the bot before linking."],
    ["أسئلة شائعة قبل الاشتراك", "Frequently asked questions"],
    ["هل يضمن البوت الربح؟", "Does the bot guarantee profit?"],
    ["هل أحتاج خبرة؟", "Do I need experience?"],
    ["هل يمكن للبوت سحب أموالي؟", "Can the bot withdraw my funds?"],
    ["كيف أتأكد من البوت؟", "How do I verify the bot?"],
    ["هل يوجد دفع يدوي؟", "Is manual payment available?"],
    ["ماذا يحدث بعد التسجيل؟", "What happens after registration?"],
    ["ابدأ الآن وشاهد النظام بنفسك", "Start now and see the system yourself"],
    ["منصة إشارات كريبتو ذكية تساعد المستخدم على تقليل العشوائية واتخاذ قرارات أوضح.", "A smart crypto signal platform that helps users reduce noise and make clearer decisions."],
    ["روابط مهمة", "Important Links"],
    ["الأقسام", "Sections"],
    ["جميع الحقوق محفوظة. التداول يحتوي على مخاطرة.", "All rights reserved. Trading involves risk."],
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
