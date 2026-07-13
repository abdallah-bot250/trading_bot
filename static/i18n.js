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
    ["Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©", "Home"],
    ["Ø§Ù„Ø¥Ø«Ø¨Ø§ØªØ§Øª", "Proof"],
    ["ØªØ¬Ø§Ø±Ø¨ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†", "User Proof"],
    ["ÙØ­Øµ Ø§Ù„Ø¨ÙˆØª", "Bot Check"],
    ["ØªØ£ÙƒØ¯ Ù…Ù† Ø§Ù„Ø¨ÙˆØª", "Verify Bot"],
    ["Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯", "Dashboard"],
    ["Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", "Dashboard"],
    ["Ø¯Ø®ÙˆÙ„", "Login"],
    ["ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„", "Login"],
    ["Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨", "Create Account"],
    ["Ø§Ø¨Ø¯Ø£ Ø§Ù„Ø¢Ù†", "Get Started"],
    ["Ø§Ø¨Ø¯Ø£ Ø§Ù„ØªØ¬Ø±Ø¨Ø©", "Start Trial"],
    ["Ø´Ø§Ù‡Ø¯ Ø§Ù„Ø¯ÙŠÙ…Ùˆ", "View Demo"],
    ["Ø´Ø§Ù‡Ø¯ Ø§Ù„Ù†ØªØ§Ø¦Ø¬", "View Results"],
    ["Ù…Ù†ØµØ© Ø¥Ø´Ø§Ø±Ø§Øª ÙƒØ±ÙŠØ¨ØªÙˆ Ø°ÙƒÙŠØ© Ù„Ù„Ù…ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø¬Ø§Ø¯", "AI crypto signal platform for serious traders"],
    ["Ø¥Ø´Ø§Ø±Ø§Øª Ù…Ù†ØªÙ‚Ø§Ø©", "Curated Signals"],
    ["Ù„ÙˆØ­Ø© ØªØ­ÙƒÙ… ÙƒØ§Ù…Ù„Ø©", "Complete Dashboard"],
    ["Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…", "Telegram Linking"],
    ["Ø¯ÙØ¹ ÙŠØ¯ÙˆÙŠ ÙˆØ£ÙˆØªÙˆÙ…Ø§ØªÙŠÙƒ", "Manual and Automatic Payments"],
    ["ØªØ¬Ø±Ø¨Ø© Ù…Ø¬Ø§Ù†ÙŠØ©", "Free Trial"],
    ["ÙƒÙŠÙ ÙŠÙÙƒØ± Ø§Ù„Ù†Ø¸Ø§Ù…ØŸ", "How the system thinks"],
    ["Ø§Ø®ØªØ¨Ø± Ø§Ù„Ù†Ø¸Ø§Ù…", "Try the System"],
    ["Ø®Ø·Ø· ÙˆØ§Ø¶Ø­Ø© Ø¨Ø¯ÙˆÙ† ØªØ¹Ù‚ÙŠØ¯", "Clear plans without friction"],
    ["Ø§ÙØªØ­ ØµÙØ­Ø© Ø§Ù„Ø¥Ø«Ø¨Ø§ØªØ§Øª", "Open Proof Page"],
    ["Ø£Ø³Ø¦Ù„Ø© Ø´Ø§Ø¦Ø¹Ø© Ù‚Ø¨Ù„ Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ", "Frequently asked questions"],
    ["Ù‡Ù„ ÙŠØ¶Ù…Ù† Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø¨Ø­ØŸ", "Does the bot guarantee profit?"],
    ["Ù‡Ù„ Ø£Ø­ØªØ§Ø¬ Ø®Ø¨Ø±Ø©ØŸ", "Do I need experience?"],
    ["Ù‡Ù„ ÙŠÙ…ÙƒÙ† Ù„Ù„Ø¨ÙˆØª Ø³Ø­Ø¨ Ø£Ù…ÙˆØ§Ù„ÙŠØŸ", "Can the bot withdraw my funds?"],
    ["ÙƒÙŠÙ Ø£ØªØ£ÙƒØ¯ Ù…Ù† Ø§Ù„Ø¨ÙˆØªØŸ", "How do I verify the bot?"],
    ["Ù‡Ù„ ÙŠÙˆØ¬Ø¯ Ø¯ÙØ¹ ÙŠØ¯ÙˆÙŠØŸ", "Is manual payment available?"],
    ["Ù…Ø§Ø°Ø§ ÙŠØ­Ø¯Ø« Ø¨Ø¹Ø¯ Ø§Ù„ØªØ³Ø¬ÙŠÙ„ØŸ", "What happens after registration?"],
    ["Ø±ÙˆØ§Ø¨Ø· Ù…Ù‡Ù…Ø©", "Important Links"],
    ["Ø§Ù„Ø£Ù‚Ø³Ø§Ù…", "Sections"],
    ["Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ", "Email Address"],
    ["ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±", "Password"],
    ["Ø§Ù„Ø§Ø³Ù… Ø§Ù„ÙƒØ§Ù…Ù„", "Full Name"],
    ["Ø§ÙƒØªØ¨ Ø§Ø³Ù…Ùƒ Ø§Ù„ÙƒØ§Ù…Ù„", "Enter your full name"],
    ["Ø£Ø¯Ø®Ù„ ÙƒÙ„Ù…Ø© Ù…Ø±ÙˆØ± Ù‚ÙˆÙŠØ©", "Enter a strong password"],
    ["Ø¥Ø¸Ù‡Ø§Ø±", "Show"],
    ["Ù„Ø¯ÙŠÙƒ Ø­Ø³Ø§Ø¨ Ø¨Ø§Ù„ÙØ¹Ù„ØŸ", "Already have an account?"],
    ["Ù„ÙŠØ³ Ù„Ø¯ÙŠÙƒ Ø­Ø³Ø§Ø¨ØŸ", "Do not have an account?"],
    ["Ù†Ø³ÙŠØª ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±ØŸ", "Forgot password?"],
    ["ÙØªØ­ Ø§Ù„Ø¨ÙˆØª", "Open Bot"],
    ["ØªØ£ÙƒØ¯ Ù…Ù† Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ", "Verify the official bot"],
    ["ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø­Ø³Ø§Ø¨", "Verify Account"],
    ["ÙƒÙˆØ¯ Ø§Ù„ØªÙØ¹ÙŠÙ„", "Verification Code"],
    ["ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø¢Ù†", "Verify Now"],
    ["ØªÙ… Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø­Ø³Ø§Ø¨", "Account Created"],
    ["Ø­Ø³Ø§Ø¨Ùƒ Ø¬Ø§Ù‡Ø² Ù„Ù„Ø§Ù†Ø·Ù„Ø§Ù‚", "Your account is ready"],
    ["Ø§Ù„Ø¯ÙØ¹", "Payment"],
    ["Ø§Ù„Ø¯ÙØ¹ Ø§Ù„ÙŠØ¯ÙˆÙŠ", "Manual Payment"],
    ["Ø³Ø¬Ù„ Ø§Ù„ÙÙˆØ§ØªÙŠØ±", "Invoice History"],
    ["Ø§Ù„Ø¯Ù„ÙŠÙ„", "Guide"],
    ["Ø§Ù„Ù…Ø¯ÙÙˆØ¹Ø§Øª", "Payments"],
    ["Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†", "Users"],
    ["Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª", "Signals"],
    ["Ø§Ù„Ø¥ÙŠØ±Ø§Ø¯Ø§Øª", "Revenue"],
    ["Ø§Ù„Ø®Ø·Ø©", "Plan"],
    ["Ø§Ù„Ø­Ø§Ù„Ø©", "Status"],
    ["ØªØ­Ø¯ÙŠØ«", "Update"],
    ["Ø­ÙØ¸", "Save"],
    ["Ø¥Ø±Ø³Ø§Ù„", "Send"],
    ["Ø¥Ù„ØºØ§Ø¡", "Cancel"],
    ["Ø±Ø¬ÙˆØ¹", "Back"],
    ["Ø§Ù„ØªØ§Ù„ÙŠ", "Next"],
    ["Ø§Ù„Ø³Ø§Ø¨Ù‚", "Previous"],
    ["ØªÙˆØ§ØµÙ„ Ù…Ø¹Ù†Ø§", "Contact"],
    ["Ù…Ù† Ù†Ø­Ù†", "About"],
    ["Ù…Ø±ÙƒØ² Ø§Ù„Ø¯Ø¹Ù…", "Support Center"],
    ["Ø§Ù„ØªÙˆØ«ÙŠÙ‚", "Documentation"],
    ["Ø³ÙŠØ§Ø³Ø© Ø§Ù„Ø®ØµÙˆØµÙŠØ©", "Privacy Policy"],
    ["Ø§Ù„Ø´Ø±ÙˆØ·", "Terms"],
    ["Ø³ÙŠØ§Ø³Ø© Ø§Ù„Ø§Ø³ØªØ±Ø¯Ø§Ø¯", "Refund Policy"],
    ["Ø¥Ø®Ù„Ø§Ø¡ Ù…Ø³Ø¤ÙˆÙ„ÙŠØ© Ø§Ù„Ù…Ø®Ø§Ø·Ø±", "Risk Disclaimer"],
    ["Ø³ÙŠØ§Ø³Ø© Ø§Ù„ÙƒÙˆÙƒÙŠØ²", "Cookie Policy"]
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
    { code: "ar", native: "Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©", name: "Arabic" },
    { code: "es", native: "EspaÃ±ol", name: "Spanish" },
    { code: "fr", native: "FranÃ§ais", name: "French" },
    { code: "de", native: "Deutsch", name: "German" },
    { code: "tr", native: "TÃ¼rkÃ§e", name: "Turkish" },
    { code: "pt", native: "PortuguÃªs", name: "Portuguese" },
    { code: "ru", native: "Ð ÑƒÑÑÐºÐ¸Ð¹", name: "Russian" },
    { code: "zh", native: "ä¸­æ–‡", name: "Chinese" },
    { code: "hi", native: "à¤¹à¤¿à¤¨à¥à¤¦à¥€", name: "Hindi" },
    { code: "ur", native: "Ø§Ø±Ø¯Ùˆ", name: "Urdu" },
    { code: "id", native: "Bahasa Indonesia", name: "Indonesian" }
  ];

  const dict = {
    ar: {
      "Home": "Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©", "Features": "Ø§Ù„Ù…Ù…ÙŠØ²Ø§Øª", "Pricing": "Ø§Ù„Ø£Ø³Ø¹Ø§Ø±", "Proof": "Ø§Ù„Ø¥Ø«Ø¨Ø§ØªØ§Øª", "Dashboard": "Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", "Login": "ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„", "Logout": "ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø®Ø±ÙˆØ¬", "Register": "Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨", "Get Started": "Ø§Ø¨Ø¯Ø£ Ø§Ù„Ø¢Ù†", "Start Free Trial": "Ø§Ø¨Ø¯Ø£ Ø§Ù„ØªØ¬Ø±Ø¨Ø© Ø§Ù„Ù…Ø¬Ø§Ù†ÙŠØ©", "Watch Demo": "Ø´Ø§Ù‡Ø¯ Ø§Ù„Ø¹Ø±Ø¶", "View Plans": "Ø¹Ø±Ø¶ Ø§Ù„Ø®Ø·Ø·", "Connect Telegram": "Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…", "Bot Check": "ÙØ­Øµ Ø§Ù„Ø¨ÙˆØª", "Manual Payment": "Ø§Ù„Ø¯ÙØ¹ Ø§Ù„ÙŠØ¯ÙˆÙŠ", "Payment": "Ø§Ù„Ø¯ÙØ¹", "Payments": "Ø§Ù„Ù…Ø¯ÙÙˆØ¹Ø§Øª", "Invoices": "Ø§Ù„ÙÙˆØ§ØªÙŠØ±", "Profile": "Ø§Ù„Ù…Ù„Ù Ø§Ù„Ø´Ø®ØµÙŠ", "Settings": "Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª", "Support": "Ø§Ù„Ø¯Ø¹Ù…", "Support Center": "Ù…Ø±ÙƒØ² Ø§Ù„Ø¯Ø¹Ù…", "Contact Support": "ØªÙˆØ§ØµÙ„ Ù…Ø¹ Ø§Ù„Ø¯Ø¹Ù…",
      "Current Plan": "Ø§Ù„Ø®Ø·Ø© Ø§Ù„Ø­Ø§Ù„ÙŠØ©", "Plan Status": "Ø­Ø§Ù„Ø© Ø§Ù„Ø®Ø·Ø©", "Subscription Status": "Ø­Ø§Ù„Ø© Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ", "Remaining Days": "Ø§Ù„Ø£ÙŠØ§Ù… Ø§Ù„Ù…ØªØ¨Ù‚ÙŠØ©", "Telegram Status": "Ø­Ø§Ù„Ø© ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…", "Connected": "Ù…ØªØµÙ„", "Not Connected": "ØºÙŠØ± Ù…ØªØµÙ„", "Active": "Ù†Ø´Ø·", "Inactive": "ØºÙŠØ± Ù†Ø´Ø·", "Free Trial": "ØªØ¬Ø±Ø¨Ø© Ù…Ø¬Ø§Ù†ÙŠØ©", "Basic": "Ø£Ø³Ø§Ø³ÙŠ", "Pro": "Ø§Ø­ØªØ±Ø§ÙÙŠ", "Elite": "Ù†Ø®Ø¨Ø©", "Pro 2 Years": "Ø¨Ø±Ùˆ Ø³Ù†ØªÙŠÙ†", "Upgrade": "ØªØ±Ù‚ÙŠØ©", "Upgrade Plan": "ØªØ±Ù‚ÙŠØ© Ø§Ù„Ø®Ø·Ø©",
      "Signals": "Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª", "Recent Signals": "Ø¢Ø®Ø± Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª", "Live Signals": "Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª Ø§Ù„Ù…Ø¨Ø§Ø´Ø±Ø©", "Get New Signals": "Ø§Ø­ØµÙ„ Ø¹Ù„Ù‰ Ø¥Ø´Ø§Ø±Ø§Øª Ø¬Ø¯ÙŠØ¯Ø©", "Auto Trading": "Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ø§Ù„ØªÙ„Ù‚Ø§Ø¦ÙŠ", "Risk Protection": "Ø­Ù…Ø§ÙŠØ© Ø§Ù„Ù…Ø®Ø§Ø·Ø±", "Signal Quality": "Ø¬ÙˆØ¯Ø© Ø§Ù„Ø¥Ø´Ø§Ø±Ø©", "Confidence": "Ø§Ù„Ø«Ù‚Ø©", "Win Rate": "Ù†Ø³Ø¨Ø© Ø§Ù„Ù†Ø¬Ø§Ø­", "Total Signals": "Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª", "Open Trades": "Ø§Ù„ØµÙÙ‚Ø§Øª Ø§Ù„Ù…ÙØªÙˆØ­Ø©", "Closed Trades": "Ø§Ù„ØµÙÙ‚Ø§Øª Ø§Ù„Ù…ØºÙ„Ù‚Ø©", "Performance": "Ø§Ù„Ø£Ø¯Ø§Ø¡", "AI Analysis": "ØªØ­Ù„ÙŠÙ„ Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ",
      "Referral": "Ø§Ù„Ø¥Ø­Ø§Ù„Ø©", "Referrals": "Ø§Ù„Ø¥Ø­Ø§Ù„Ø§Øª", "Invite & Earn": "Ø§Ø¯Ø¹ ÙˆØ§Ø±Ø¨Ø­", "Referral Link": "Ø±Ø§Ø¨Ø· Ø§Ù„Ø¥Ø­Ø§Ù„Ø©", "Copy": "Ù†Ø³Ø®", "Copied": "ØªÙ… Ø§Ù„Ù†Ø³Ø®", "Free Earn": "Ø§Ø±Ø¨Ø­ Ù…Ø¬Ø§Ù†Ù‹Ø§", "Watch Video & Unlock": "Ø´Ø§Ù‡Ø¯ Ø§Ù„ÙÙŠØ¯ÙŠÙˆ ÙˆØ§ÙØªØ­ Ø§Ù„Ø¥Ø´Ø§Ø±Ø©", "Upgrade: No Ads": "ØªØ±Ù‚ÙŠØ© Ø¨Ø¯ÙˆÙ† Ø¥Ø¹Ù„Ø§Ù†Ø§Øª",
      "Admin Overview": "Ù†Ø¸Ø±Ø© Ø¹Ø§Ù…Ø© Ù„Ù„Ø£Ø¯Ù…Ù†", "Users": "Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙˆÙ†", "Subscriptions": "Ø§Ù„Ø§Ø´ØªØ±Ø§ÙƒØ§Øª", "Revenue": "Ø§Ù„Ø¥ÙŠØ±Ø§Ø¯Ø§Øª", "System Health": "ØµØ­Ø© Ø§Ù„Ù†Ø¸Ø§Ù…", "Maintenance": "Ø§Ù„ØµÙŠØ§Ù†Ø©", "Search users": "Ø§Ù„Ø¨Ø­Ø« Ø¹Ù† Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†", "Actions": "Ø§Ù„Ø¥Ø¬Ø±Ø§Ø¡Ø§Øª",
      "Email Address": "Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ", "Password": "ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±", "Full Name": "Ø§Ù„Ø§Ø³Ù… Ø§Ù„ÙƒØ§Ù…Ù„", "Forgot password?": "Ù†Ø³ÙŠØª ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±ØŸ", "Create Account": "Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨", "Already have an account?": "Ù„Ø¯ÙŠÙƒ Ø­Ø³Ø§Ø¨ Ø¨Ø§Ù„ÙØ¹Ù„ØŸ", "Open Bot": "ÙØªØ­ Ø§Ù„Ø¨ÙˆØª", "Verify Bot": "ØªØ£ÙƒÙŠØ¯ Ø§Ù„Ø¨ÙˆØª", "Save": "Ø­ÙØ¸", "Cancel": "Ø¥Ù„ØºØ§Ø¡", "Back": "Ø±Ø¬ÙˆØ¹", "Next": "Ø§Ù„ØªØ§Ù„ÙŠ", "Send": "Ø¥Ø±Ø³Ø§Ù„", "Language": "Ø§Ù„Ù„ØºØ©"
    },
    es: {
      "Home": "Inicio", "Features": "Funciones", "Pricing": "Precios", "Proof": "Pruebas", "Dashboard": "Panel", "Login": "Iniciar sesiÃ³n", "Logout": "Salir", "Register": "Registro", "Get Started": "Empezar", "Start Free Trial": "Prueba gratis", "Watch Demo": "Ver demo", "View Plans": "Ver planes", "Connect Telegram": "Conectar Telegram", "Bot Check": "Verificar bot", "Manual Payment": "Pago manual", "Payment": "Pago", "Payments": "Pagos", "Invoices": "Facturas", "Profile": "Perfil", "Settings": "Ajustes", "Support": "Soporte",
      "Current Plan": "Plan actual", "Plan Status": "Estado del plan", "Subscription Status": "Estado de suscripciÃ³n", "Remaining Days": "DÃ­as restantes", "Telegram Status": "Estado de Telegram", "Connected": "Conectado", "Not Connected": "No conectado", "Active": "Activo", "Inactive": "Inactivo", "Upgrade Plan": "Mejorar plan",
      "Signals": "SeÃ±ales", "Recent Signals": "SeÃ±ales recientes", "Live Signals": "SeÃ±ales en vivo", "Auto Trading": "Trading automÃ¡tico", "Risk Protection": "ProtecciÃ³n de riesgo", "Confidence": "Confianza", "Win Rate": "Tasa de acierto", "Total Signals": "SeÃ±ales totales", "Performance": "Rendimiento", "AI Analysis": "AnÃ¡lisis de IA",
      "Referrals": "Referidos", "Invite & Earn": "Invita y gana", "Email Address": "Correo electrÃ³nico", "Password": "ContraseÃ±a", "Full Name": "Nombre completo", "Forgot password?": "Â¿Olvidaste tu contraseÃ±a?", "Create Account": "Crear cuenta", "Open Bot": "Abrir bot", "Save": "Guardar", "Cancel": "Cancelar", "Language": "Idioma"
    },
    fr: {
      "Home": "Accueil", "Features": "FonctionnalitÃ©s", "Pricing": "Tarifs", "Proof": "Preuves", "Dashboard": "Tableau de bord", "Login": "Connexion", "Logout": "DÃ©connexion", "Register": "Inscription", "Get Started": "Commencer", "Start Free Trial": "Essai gratuit", "Watch Demo": "Voir la dÃ©mo", "View Plans": "Voir les plans", "Connect Telegram": "Connecter Telegram", "Bot Check": "VÃ©rifier le bot", "Payment": "Paiement", "Payments": "Paiements", "Invoices": "Factures", "Profile": "Profil", "Settings": "ParamÃ¨tres", "Support": "Support",
      "Current Plan": "Plan actuel", "Subscription Status": "Statut d'abonnement", "Remaining Days": "Jours restants", "Telegram Status": "Statut Telegram", "Connected": "ConnectÃ©", "Not Connected": "Non connectÃ©", "Active": "Actif", "Upgrade Plan": "AmÃ©liorer le plan", "Signals": "Signaux", "Recent Signals": "Signaux rÃ©cents", "Auto Trading": "Trading automatique", "Risk Protection": "Protection du risque", "Confidence": "Confiance", "Win Rate": "Taux de rÃ©ussite", "Performance": "Performance", "AI Analysis": "Analyse IA", "Language": "Langue"
    },
    de: {
      "Home": "Start", "Features": "Funktionen", "Pricing": "Preise", "Proof": "Nachweise", "Dashboard": "Dashboard", "Login": "Anmelden", "Logout": "Abmelden", "Register": "Registrieren", "Get Started": "Loslegen", "Start Free Trial": "Kostenlos starten", "Watch Demo": "Demo ansehen", "View Plans": "PlÃ¤ne ansehen", "Connect Telegram": "Telegram verbinden", "Payment": "Zahlung", "Payments": "Zahlungen", "Invoices": "Rechnungen", "Profile": "Profil", "Settings": "Einstellungen", "Support": "Support", "Current Plan": "Aktueller Plan", "Subscription Status": "Abo-Status", "Remaining Days": "Verbleibende Tage", "Telegram Status": "Telegram-Status", "Connected": "Verbunden", "Active": "Aktiv", "Signals": "Signale", "Recent Signals": "Letzte Signale", "Auto Trading": "Auto-Trading", "Risk Protection": "Risik Schutz", "Confidence": "Vertrauen", "Language": "Sprache"
    },
    tr: {
      "Home": "Ana Sayfa", "Features": "Ã–zellikler", "Pricing": "Fiyatlar", "Proof": "KanÄ±t", "Dashboard": "Panel", "Login": "GiriÅŸ", "Logout": "Ã‡Ä±kÄ±ÅŸ", "Register": "KayÄ±t", "Get Started": "BaÅŸla", "Start Free Trial": "Ãœcretsiz dene", "Watch Demo": "Demoyu izle", "View Plans": "PlanlarÄ± gÃ¶r", "Connect Telegram": "Telegram baÄŸla", "Payment": "Ã–deme", "Payments": "Ã–demeler", "Invoices": "Faturalar", "Profile": "Profil", "Settings": "Ayarlar", "Support": "Destek", "Current Plan": "Mevcut plan", "Subscription Status": "Abonelik durumu", "Remaining Days": "Kalan gÃ¼n", "Telegram Status": "Telegram durumu", "Connected": "BaÄŸlÄ±", "Signals": "Sinyaller", "Recent Signals": "Son sinyaller", "Auto Trading": "Otomatik iÅŸlem", "Risk Protection": "Risk korumasÄ±", "Language": "Dil"
    },
    pt: {
      "Home": "InÃ­cio", "Features": "Recursos", "Pricing": "PreÃ§os", "Proof": "Provas", "Dashboard": "Painel", "Login": "Entrar", "Logout": "Sair", "Register": "Registrar", "Get Started": "ComeÃ§ar", "Start Free Trial": "Teste grÃ¡tis", "Watch Demo": "Ver demo", "View Plans": "Ver planos", "Connect Telegram": "Conectar Telegram", "Payment": "Pagamento", "Payments": "Pagamentos", "Invoices": "Faturas", "Profile": "Perfil", "Settings": "ConfiguraÃ§Ãµes", "Support": "Suporte", "Current Plan": "Plano atual", "Subscription Status": "Status da assinatura", "Remaining Days": "Dias restantes", "Telegram Status": "Status do Telegram", "Connected": "Conectado", "Signals": "Sinais", "Recent Signals": "Sinais recentes", "Auto Trading": "Trading automÃ¡tico", "Risk Protection": "ProteÃ§Ã£o de risco", "Language": "Idioma"
    },
    ru: {
      "Home": "Ð“Ð»Ð°Ð²Ð½Ð°Ñ", "Features": "Ð¤ÑƒÐ½ÐºÑ†Ð¸Ð¸", "Pricing": "Ð¦ÐµÐ½Ñ‹", "Proof": "Ð”Ð¾ÐºÐ°Ð·Ð°Ñ‚ÐµÐ»ÑŒÑÑ‚Ð²Ð°", "Dashboard": "ÐŸÐ°Ð½ÐµÐ»ÑŒ", "Login": "Ð’Ð¾Ð¹Ñ‚Ð¸", "Logout": "Ð’Ñ‹Ð¹Ñ‚Ð¸", "Register": "Ð ÐµÐ³Ð¸ÑÑ‚Ñ€Ð°Ñ†Ð¸Ñ", "Get Started": "ÐÐ°Ñ‡Ð°Ñ‚ÑŒ", "Start Free Trial": "Ð‘ÐµÑÐ¿Ð»Ð°Ñ‚Ð½Ñ‹Ð¹ ÑÑ‚Ð°Ñ€Ñ‚", "Watch Demo": "Ð¡Ð¼Ð¾Ñ‚Ñ€ÐµÑ‚ÑŒ Ð´ÐµÐ¼Ð¾", "View Plans": "ÐŸÐ»Ð°Ð½Ñ‹", "Connect Telegram": "ÐŸÐ¾Ð´ÐºÐ»ÑŽÑ‡Ð¸Ñ‚ÑŒ Telegram", "Payment": "ÐžÐ¿Ð»Ð°Ñ‚Ð°", "Payments": "ÐŸÐ»Ð°Ñ‚ÐµÐ¶Ð¸", "Invoices": "Ð¡Ñ‡ÐµÑ‚Ð°", "Profile": "ÐŸÑ€Ð¾Ñ„Ð¸Ð»ÑŒ", "Settings": "ÐÐ°ÑÑ‚Ñ€Ð¾Ð¹ÐºÐ¸", "Support": "ÐŸÐ¾Ð´Ð´ÐµÑ€Ð¶ÐºÐ°", "Current Plan": "Ð¢ÐµÐºÑƒÑ‰Ð¸Ð¹ Ð¿Ð»Ð°Ð½", "Subscription Status": "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐ¸", "Remaining Days": "ÐžÑÑ‚Ð°Ð»Ð¾ÑÑŒ Ð´Ð½ÐµÐ¹", "Telegram Status": "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ Telegram", "Connected": "ÐŸÐ¾Ð´ÐºÐ»ÑŽÑ‡ÐµÐ½Ð¾", "Signals": "Ð¡Ð¸Ð³Ð½Ð°Ð»Ñ‹", "Recent Signals": "ÐŸÐ¾ÑÐ»ÐµÐ´Ð½Ð¸Ðµ ÑÐ¸Ð³Ð½Ð°Ð»Ñ‹", "Auto Trading": "ÐÐ²Ñ‚Ð¾Ñ‚Ð¾Ñ€Ð³Ð¾Ð²Ð»Ñ", "Risk Protection": "Ð—Ð°Ñ‰Ð¸Ñ‚Ð° Ñ€Ð¸ÑÐºÐ°", "Language": "Ð¯Ð·Ñ‹Ðº"
    },
    zh: {
      "Home": "é¦–é¡µ", "Features": "åŠŸèƒ½", "Pricing": "ä»·æ ¼", "Proof": "è¯æ˜Ž", "Dashboard": "æŽ§åˆ¶å°", "Login": "ç™»å½•", "Logout": "é€€å‡º", "Register": "æ³¨å†Œ", "Get Started": "å¼€å§‹", "Start Free Trial": "å…è´¹è¯•ç”¨", "Watch Demo": "è§‚çœ‹æ¼”ç¤º", "View Plans": "æŸ¥çœ‹å¥—é¤", "Connect Telegram": "è¿žæŽ¥ Telegram", "Payment": "æ”¯ä»˜", "Payments": "ä»˜æ¬¾", "Invoices": "å‘ç¥¨", "Profile": "èµ„æ–™", "Settings": "è®¾ç½®", "Support": "æ”¯æŒ", "Current Plan": "å½“å‰å¥—é¤", "Subscription Status": "è®¢é˜…çŠ¶æ€", "Remaining Days": "å‰©ä½™å¤©æ•°", "Telegram Status": "Telegram çŠ¶æ€", "Connected": "å·²è¿žæŽ¥", "Signals": "ä¿¡å·", "Recent Signals": "æœ€æ–°ä¿¡å·", "Auto Trading": "è‡ªåŠ¨äº¤æ˜“", "Risk Protection": "é£Žé™©ä¿æŠ¤", "Language": "è¯­è¨€"
    },
    hi: {
      "Home": "à¤¹à¥‹à¤®", "Features": "à¤«à¥€à¤šà¤°à¥à¤¸", "Pricing": "à¤•à¥€à¤®à¤¤", "Proof": "à¤ªà¥à¤°à¥‚à¤«", "Dashboard": "à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡", "Login": "à¤²à¥‰à¤—à¤¿à¤¨", "Logout": "à¤²à¥‰à¤—à¤†à¤‰à¤Ÿ", "Register": "à¤°à¤œà¤¿à¤¸à¥à¤Ÿà¤°", "Get Started": "à¤¶à¥à¤°à¥‚ à¤•à¤°à¥‡à¤‚", "Start Free Trial": "à¤«à¥à¤°à¥€ à¤Ÿà¥à¤°à¤¾à¤¯à¤²", "Watch Demo": "à¤¡à¥‡à¤®à¥‹ à¤¦à¥‡à¤–à¥‡à¤‚", "View Plans": "à¤ªà¥à¤²à¤¾à¤¨ à¤¦à¥‡à¤–à¥‡à¤‚", "Connect Telegram": "Telegram à¤œà¥‹à¤¡à¤¼à¥‡à¤‚", "Payment": "à¤­à¥à¤—à¤¤à¤¾à¤¨", "Payments": "à¤­à¥à¤—à¤¤à¤¾à¤¨", "Invoices": "à¤‡à¤¨à¤µà¥‰à¤‡à¤¸", "Profile": "à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤²", "Settings": "à¤¸à¥‡à¤Ÿà¤¿à¤‚à¤—à¥à¤¸", "Support": "à¤¸à¤ªà¥‹à¤°à¥à¤Ÿ", "Current Plan": "à¤®à¥Œà¤œà¥‚à¤¦à¤¾ à¤ªà¥à¤²à¤¾à¤¨", "Subscription Status": "à¤¸à¤¬à¥à¤¸à¤•à¥à¤°à¤¿à¤ªà¥à¤¶à¤¨ à¤¸à¥à¤¥à¤¿à¤¤à¤¿", "Remaining Days": "à¤¬à¤šà¥‡ à¤¦à¤¿à¤¨", "Telegram Status": "Telegram à¤¸à¥à¤¥à¤¿à¤¤à¤¿", "Connected": "à¤•à¤¨à¥‡à¤•à¥à¤Ÿà¥‡à¤¡", "Signals": "à¤¸à¤¿à¤—à¥à¤¨à¤²", "Recent Signals": "à¤¹à¤¾à¤² à¤•à¥‡ à¤¸à¤¿à¤—à¥à¤¨à¤²", "Auto Trading": "à¤‘à¤Ÿà¥‹ à¤Ÿà¥à¤°à¥‡à¤¡à¤¿à¤‚à¤—", "Risk Protection": "à¤°à¤¿à¤¸à¥à¤• à¤¸à¥à¤°à¤•à¥à¤·à¤¾", "Language": "à¤­à¤¾à¤·à¤¾"
    },
    ur: {
      "Home": "ÛÙˆÙ…", "Features": "Ø®ØµÙˆØµÛŒØ§Øª", "Pricing": "Ù‚ÛŒÙ…ØªÛŒÚº", "Proof": "Ø«Ø¨ÙˆØª", "Dashboard": "ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ", "Login": "Ù„Ø§Ú¯ Ø§Ù†", "Logout": "Ù„Ø§Ú¯ Ø¢Ø¤Ù¹", "Register": "Ø±Ø¬Ø³Ù¹Ø±", "Get Started": "Ø´Ø±ÙˆØ¹ Ú©Ø±ÛŒÚº", "Start Free Trial": "Ù…ÙØª Ù¹Ø±Ø§Ø¦Ù„", "Watch Demo": "ÚˆÛŒÙ…Ùˆ Ø¯ÛŒÚ©Ú¾ÛŒÚº", "View Plans": "Ù¾Ù„Ø§Ù† Ø¯ÛŒÚ©Ú¾ÛŒÚº", "Connect Telegram": "Telegram Ø¬ÙˆÚ‘ÛŒÚº", "Payment": "Ø§Ø¯Ø§Ø¦ÛŒÚ¯ÛŒ", "Payments": "Ø§Ø¯Ø§Ø¦ÛŒÚ¯ÛŒØ§Úº", "Invoices": "Ø§Ù†ÙˆØ§Ø¦Ø³Ø²", "Profile": "Ù¾Ø±ÙˆÙØ§Ø¦Ù„", "Settings": "Ø³ÛŒÙ¹Ù†Ú¯Ø²", "Support": "Ø³Ù¾ÙˆØ±Ù¹", "Current Plan": "Ù…ÙˆØ¬ÙˆØ¯Û Ù¾Ù„Ø§Ù†", "Subscription Status": "Ø³Ø¨Ø³Ú©Ø±Ù¾Ø´Ù† Ú©ÛŒ Ø­Ø§Ù„Øª", "Remaining Days": "Ø¨Ø§Ù‚ÛŒ Ø¯Ù†", "Telegram Status": "Telegram Ø­Ø§Ù„Øª", "Connected": "Ù…Ù†Ø³Ù„Ú©", "Signals": "Ø³Ú¯Ù†Ù„Ø²", "Recent Signals": "Ø­Ø§Ù„ÛŒÛ Ø³Ú¯Ù†Ù„Ø²", "Auto Trading": "Ø¢Ù¹Ùˆ Ù¹Ø±ÛŒÚˆÙ†Ú¯", "Risk Protection": "Ø±Ø³Ú© ØªØ­ÙØ¸", "Language": "Ø²Ø¨Ø§Ù†"
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
        '<span class="nx-language-globe">â—Ž</span>',
        '<span class="nx-language-code">' + active.code.toUpperCase() + '</span>',
        '<span class="nx-language-name">' + active.native + '</span>',
        '<span class="nx-language-caret">âŒ„</span>',
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

  const copy = {
    en: {
      "ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„": "Login",
      "Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨": "Create Account",
      "Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨ Ø¬Ø¯ÙŠØ¯": "Create New Account",
      "Ø§Ù„Ø§Ø³Ù… Ø§Ù„ÙƒØ§Ù…Ù„": "Full Name",
      "Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ": "Email Address",
      "ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±": "Password",
      "Ø£Ø¯Ø®Ù„ Ø§Ø³Ù…Ùƒ Ø§Ù„ÙƒØ§Ù…Ù„": "Enter your full name",
      "Ø£Ø¯Ø®Ù„ Ø¨Ø±ÙŠØ¯Ùƒ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ": "Enter your email address",
      "Ø£Ø¯Ø®Ù„ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±": "Enter your password",
      "Ù„Ø¯ÙŠÙƒ Ø­Ø³Ø§Ø¨ Ø¨Ø§Ù„ÙØ¹Ù„ØŸ": "Already have an account?",
      "Ù†Ø³ÙŠØª ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±ØŸ": "Forgot password?",
      "Ù…Ø±Ø­Ø¨Ù‹Ø§ Ø¨Ø¹ÙˆØ¯ØªÙƒØŒ Ø§Ø¯Ø®Ù„ Ù„Ø­Ø³Ø§Ø¨Ùƒ ÙˆØ±Ø¨Ø· Ø§Ù„Ø¨ÙˆØª Ø¨Ø³Ù‡ÙˆÙ„Ø©.": "Welcome back. Sign in to your account and connect the bot easily.",
      "Ø¨Ø¹Ø¯ Ø§Ù„Ø¯Ø®ÙˆÙ„ ÙŠÙ…ÙƒÙ†Ùƒ ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø®Ø·Ø©ØŒ Ù…Ø±Ø§Ø¬Ø¹Ø© Ø§Ù„ÙÙˆØ§ØªÙŠØ±ØŒ ÙˆØ±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… Ø¨Ø£Ù…Ø§Ù†.": "After login, you can activate your plan, review invoices, and link Telegram safely.",
      "Ø§ÙØªØ­ Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ ÙˆØ§ØªØ¨Ø¹ Ø±Ø§Ø¨Ø· Ø§Ù„Ø±Ø¨Ø· Ø§Ù„Ø¢Ù…Ù†ØŒ Ø«Ù… Ø³Ø¬Ù„ Ø¯Ø®ÙˆÙ„Ùƒ Ù…Ù† Ø§Ù„Ù…ÙˆÙ‚Ø¹ Ù„ØªØ£ÙƒÙŠØ¯ Ø§Ù„Ø­Ø³Ø§Ø¨.": "Open the official bot, follow the secure linking flow, then sign in on the website to confirm your account.",
      "Ù…Ø´ Ø¨ØªÙˆØµÙ„Ùƒ SignalsØŸ": "Not receiving signals?",
      "Verify Bot Ø§Ù„Ø±Ø³Ù…ÙŠ": "Verify Official Bot",
      "Ø§Ø¨Ø¯Ø£ Ø±Ø­Ù„ØªÙƒ Ø§Ù„Ø§Ø­ØªØ±Ø§ÙÙŠØ©": "Start your professional journey",
      "Ù…Ø¹ Nexora AI Trader": "with Nexora AI Trader",
      "Ø§Ù†Ø¶Ù… Ø¥Ù„Ù‰ Ø§Ù„Ù…ØªØ¯Ø§ÙˆÙ„ÙŠÙ† Ø§Ù„Ø°ÙŠÙ† ÙŠØ¹ØªÙ…Ø¯ÙˆÙ† Ø¹Ù„Ù‰ Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ Ù„Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø¥Ø´Ø§Ø±Ø§Øª Ø¯Ù‚ÙŠÙ‚Ø© ÙˆØ¢Ù…Ù†Ø© ÙÙŠ Ø³ÙˆÙ‚ Ø§Ù„Ø¹Ù…Ù„Ø§Øª Ø§Ù„Ø±Ù‚Ù…ÙŠØ©.": "Join traders using AI-assisted crypto signal intelligence with risk-managed delivery.",
      "Ø¥Ø´Ø§Ø±Ø§Øª Ø¯Ù‚ÙŠÙ‚Ø©": "Precise Signals",
      "Ø­Ù…Ø§ÙŠØ© Ø°ÙƒÙŠØ©": "Smart Protection",
      "Ù†ØªØ§Ø¦Ø¬ Ù†Ù…ÙˆØ°Ø¬ÙŠØ©": "Structured Results",
      "Ù…ØªØ¯Ø§ÙˆÙ„ Ù†Ø´Ø·": "Active Traders",
      "Ø¯Ù‚Ø© Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª": "Signal Accuracy",
      "Ø¯Ø¹Ù… ÙÙ†ÙŠ": "Support",
      "Ø¥Ø´Ø§Ø±Ø© Ù†Ø§Ø¬Ø­Ø©": "Tracked Signals",
      "Ø¨Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø­Ø³Ø§Ø¨ Ø£Ù†Øª ØªÙˆØ§ÙÙ‚ Ø¹Ù„Ù‰ Ø§Ù„Ø´Ø±ÙˆØ· ÙˆØ§Ù„Ø£Ø­ÙƒØ§Ù… ÙˆØ³ÙŠØ§Ø³Ø© Ø§Ù„Ø®ØµÙˆØµÙŠØ©. Ø§ÙØªØ­ Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ Ø¨Ø¹Ø¯ Ø§Ù„ØªØ³Ø¬ÙŠÙ„ Ù„Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù….": "By creating an account, you agree to the terms and privacy policy. Open the official bot after registration to link Telegram.",
      "Ø±Ø¬ÙˆØ¹ Ù„Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯": "Back to Dashboard",
      "ØµÙØ­Ø© Ø§Ù„Ø¥Ø«Ø¨Ø§ØªØ§Øª": "Proof Page",
      "ÙØ­Øµ Ø§Ù„Ø¨ÙˆØª": "Bot Check",
      "Ù„ÙˆØ­Ø© ØªØ­ÙƒÙ… Ø§Ù„Ø£Ø¯Ù…Ù†": "Admin Control Center",
      "Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†ØŒ Ø§Ù„Ø®Ø·Ø·ØŒ ÙˆØ±Ø¨Ø· Ø§Ù„Ø¨ÙˆØª Ù…Ù† Ù…ÙƒØ§Ù† ÙˆØ§Ø­Ø¯": "Manage users, plans, and bot connectivity from one place",
      "Ù‡Ù†Ø§ ØªÙ‚Ø¯Ø± ØªØªØ§Ø¨Ø¹ Ø£Ø±Ù‚Ø§Ù… Ø§Ù„Ù…Ø´Ø±ÙˆØ¹ Ø¨Ø³Ø±Ø¹Ø©ØŒ ØªÙØ¹Ù„ Ø£ÙŠ Ø®Ø·Ø© ÙŠØ¯ÙˆÙŠØŒ ØªØ±Ø§Ø¬Ø¹ Ø±Ø¨Ø· ØªÙ„ÙŠØ¬Ø±Ø§Ù…ØŒ ÙˆØªØºÙ„Ù‚ Ø·Ù„Ø¨Ø§Øª Ø§Ù„Ø³Ø­Ø¨ Ù…Ù† ØºÙŠØ± Ù…Ø§ ØªØ¯Ø®Ù„ Ø¹Ù„Ù‰ Ø£ÙƒØ«Ø± Ù…Ù† Ù…ÙƒØ§Ù†.": "Monitor project metrics, manually activate plans, review Telegram linking, and process withdrawals from one control center.",
      "Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†": "Total Users",
      "Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ† Ù…Ø¯ÙÙˆØ¹ÙŠÙ†": "Paid Users",
      "Ø¥ÙŠØ±Ø§Ø¯ Ø§Ù„Ø®Ø·Ø·": "Plan Revenue",
      "Ø³Ø­ÙˆØ¨Ø§Øª Ù…Ø¹Ù„Ù‚Ø©": "Pending Withdrawals",
      "Ø­Ø§Ù„Ø© Ø§Ù„ØªØ´ØºÙŠÙ„": "Operating Status",
      "Ø­Ø³Ø§Ø¨Ø§Øª Ù…Ø±Ø¨ÙˆØ·Ø© Ø¨ØªÙ„ÙŠØ¬Ø±Ø§Ù…": "Telegram Linked Accounts",
      "Ø¨ÙˆØªØ§Øª Ù…ÙØ¹Ù„Ø©": "Active Bots",
      "Ø¹Ù…ÙˆÙ„Ø§Øª Affiliate Ù…Ø³Ø¬Ù„Ø©": "Recorded Affiliate Commissions",
      "Ù‚ÙŠÙ…Ø© Ø§Ù„Ø³Ø­ÙˆØ¨Ø§Øª Ø§Ù„Ù…Ø¹Ù„Ù‚Ø©": "Pending Withdrawal Value",
      "Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†": "User Management",
      "Ø¨Ø­Ø«ØŒ ÙÙ„ØªØ±Ø©ØŒ ÙˆØªÙØ¹ÙŠÙ„ Ø®Ø·Ø· Basic Ùˆ Pro Ùˆ Elite Ùˆ Pro 2 Years Ø¨Ø¯ÙˆÙ† ØªØºÙŠÙŠØ± Ù…Ø³Ø§Ø± Ø§Ù„Ø¯ÙØ¹.": "Search, filter, and activate Basic, Pro, Elite, and Pro 2 Years without changing the payment flow.",
      "ÙƒÙ„ Ø§Ù„Ø®Ø·Ø·": "All Plans",
      "ÙƒÙ„ Ø§Ù„Ø­Ø§Ù„Ø§Øª": "All Statuses",
      "Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…": "User",
      "Ø§Ù„Ø®Ø·Ø©": "Plan",
      "Ø§Ù„Ø¯ÙØ¹": "Payment",
      "ØªØ§Ø±ÙŠØ® Ø§Ù„Ø§Ù†ØªÙ‡Ø§Ø¡": "Expiry Date",
      "Ø§Ù„ØªØ­ÙƒÙ…": "Control",
      "Ø·Ù„Ø¨Ø§Øª Ø³Ø­Ø¨ Ø§Ù„Ø£Ø±Ø¨Ø§Ø­": "Affiliate Withdrawal Requests",
      "Ø±Ø§Ø¬Ø¹ Ø§Ù„Ù…Ø­Ø§ÙØ¸ ÙˆØ§Ù„Ù…Ø¨Ø§Ù„ØºØŒ Ø«Ù… Ø¹Ù„Ù… Ø§Ù„Ø·Ù„Ø¨ ÙƒÙ…Ø¯ÙÙˆØ¹ Ø¨Ø¹Ø¯ Ø§Ù„ØªØ­ÙˆÙŠÙ„.": "Review wallets and amounts, then mark requests as paid after transfer.",
      "Ø§Ø¨Ø­Ø« Ø¨Ù…Ø­ÙØ¸Ø© Ø£Ùˆ Chat ID": "Search by wallet or Chat ID",
      "ÙƒÙ„ Ø§Ù„Ø·Ù„Ø¨Ø§Øª": "All Requests",
      "ØªÙ… Ù†Ø³Ø® Ø±Ø§Ø¨Ø· Ø§Ù„Ø¥Ø­Ø§Ù„Ø©": "Referral link copied",
      "Ø§Ù„Ù†ØªØ§Ø¦Ø¬ Ø§Ù„Ù…Ø¹Ø±ÙˆØ¶Ø© Ù‡Ù†Ø§ Ù…Ø±ØªØ¨Ø·Ø© Ø¨Ø­Ø³Ø§Ø¨Ùƒ ÙˆØ¨ÙŠØ§Ù†Ø§Øª ØªØ¯Ø§ÙˆÙ„Ùƒ Ø§Ù„Ø­Ø§Ù„ÙŠØ©": "The results shown here are linked to your account and current trading data",
      "Ø£Ø¯Ø§Ø¡ Ø§Ù„Ø£Ø±Ø¨Ø§Ø­ ÙŠØªÙ… ØªØ­Ø¯ÙŠØ«Ù‡ ØªÙ„Ù‚Ø§Ø¦ÙŠÙ‹Ø§": "Profit performance updates automatically",
      "ØªØ­ÙƒÙ… ÙÙŠ Ø£Ù†ÙˆØ§Ø¹ Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª Ø§Ù„ØªÙŠ ÙŠØ³ØªÙ‚Ø¨Ù„Ù‡Ø§ Ø­Ø³Ø§Ø¨Ùƒ. Ø§Ù„Ù…Ø­Ø±Ùƒ Ø³ÙŠÙ‚ÙŠÙ‘Ù… Spot Ùˆ Futures Ø¨Ø´ÙƒÙ„ Ù…Ø³ØªÙ‚Ù„ ÙˆÙŠØ®ØªØ§Ø± Ø§Ù„Ø£ÙØ¶Ù„ Ø­Ø³Ø¨ Ø§Ù„Ø¬ÙˆØ¯Ø©.": "Control which signal types your account receives. The engine evaluates Spot and Futures independently and selects opportunities by quality.",
      "ØªÙØ¹ÙŠÙ„ Ø£Ùˆ Ø¥ÙŠÙ‚Ø§Ù ÙØ±Øµ Spot": "Enable or disable Spot opportunities",
      "ØªÙØ¹ÙŠÙ„ Ø£Ùˆ Ø¥ÙŠÙ‚Ø§Ù ÙØ±Øµ Futures": "Enable or disable Futures opportunities",
      "Ø§Ø±Ø¨Ø· Ø§Ù„Ù€ API Ø§Ù„Ø®Ø§Øµ Ø¨Ùƒ ÙˆØ§Ø¶Ø¨Ø· Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„ØªØ¯Ø§ÙˆÙ„ â€” Ø§Ù„Ø¨ÙˆØª Ù„Ø§ ÙŠØ³ØªØ·ÙŠØ¹ Ø§Ù„Ø³Ø­Ø¨ Ø£Ùˆ Ø§Ù„Ø¥ÙŠØ¯Ø§Ø¹ØŒ ÙÙ‚Ø· ØªÙ†ÙÙŠØ° Ø§Ù„ØµÙÙ‚Ø§Øª.": "Connect your API and configure trading settings. The bot cannot withdraw or deposit; it can only execute trades.",
      "Ø±Ø¨Ø· API": "API Connection",
      "Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„ØªØ¯Ø§ÙˆÙ„": "Trading Settings",
      "Ø§Ø³ØªÙ‚Ø¨Ø§Ù„ ÙØ±Øµ Spot Ø¹Ù†Ø¯ Ø§Ù„Ø¬ÙˆØ¯Ø© Ø§Ù„Ù…Ù†Ø§Ø³Ø¨Ø©": "Receive Spot opportunities when quality is suitable",
      "Ø§Ø³ØªÙ‚Ø¨Ø§Ù„ ÙØ±Øµ Futures Ø¹Ù†Ø¯ Ø§Ù„Ø¬ÙˆØ¯Ø© Ø§Ù„Ù…Ù†Ø§Ø³Ø¨Ø©": "Receive Futures opportunities when quality is suitable",
      "ÙƒÙ„ Basic +": "All Basic +",
      "ÙƒÙ„ Pro +": "All Pro +"
    },
    ar: {
      "Nexora AI Trader is a risk-managed AI crypto signal platform with SMC, support and resistance targets, Telegram delivery, dashboard tracking, and a free trial.": "Nexora AI Trader Ù…Ù†ØµØ© Ø¥Ø´Ø§Ø±Ø§Øª ÙƒØ±ÙŠØ¨ØªÙˆ Ù…Ø¯Ø¹ÙˆÙ…Ø© Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ Ù…Ø¹ Ø¥Ø¯Ø§Ø±Ø© Ù…Ø®Ø§Ø·Ø±ØŒ Ø£Ù‡Ø¯Ø§Ù Ø¯Ø¹Ù… ÙˆÙ…Ù‚Ø§ÙˆÙ…Ø©ØŒ ØªÙˆØµÙŠÙ„ Ø¹Ø¨Ø± ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…ØŒ ØªØªØ¨Ø¹ Ù…Ù† Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ØŒ ÙˆØªØ¬Ø±Ø¨Ø© Ù…Ø¬Ø§Ù†ÙŠØ©.",
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Ù…Ù†ØµØ© Ø¥Ø´Ø§Ø±Ø§Øª ÙƒØ±ÙŠØ¨ØªÙˆ Ù…Ø¯Ø¹ÙˆÙ…Ø© Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ Ù…Ø¹ ØªÙ†Ø¨ÙŠÙ‡Ø§Øª ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… ÙˆØ¥Ø¯Ø§Ø±Ø© Ù…Ø®Ø§Ø·Ø± ÙˆØªØªØ¨Ø¹ Ù…Ù† Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯.",
      "AI crypto signal platform for serious traders": "Ù…Ù†ØµØ© Ø¥Ø´Ø§Ø±Ø§Øª ÙƒØ±ÙŠØ¨ØªÙˆ Ø°ÙƒÙŠØ© Ù„Ù„Ù…ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø¬Ø§Ø¯",
      "Professional BTC/USDT trading terminal.": "Ù…Ù†ØµØ© ØªØ¯Ø§ÙˆÙ„ Ø§Ø­ØªØ±Ø§ÙÙŠØ© BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Ø¹Ø±Ø¶ TradingView ÙƒØ§Ù…Ù„ Ù„Ù‚Ø±Ø§Ø¡Ø© Ø§Ù„Ø§ØªØ¬Ø§Ù‡ ÙˆØ­Ø±ÙƒØ© Ø§Ù„Ø³Ø¹Ø± ÙˆÙ…Ø±Ø§Ø¬Ø¹Ø© Ø§Ù„Ø³ÙˆÙ‚ Ù‚Ø¨Ù„ ÙØªØ­ Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯.",
      "Built for traders who want clarity before entry.": "Ù…ØµÙ…Ù… Ù„Ù„Ù…ØªØ¯Ø§ÙˆÙ„ÙŠÙ† Ø§Ù„Ø°ÙŠÙ† ÙŠØ±ÙŠØ¯ÙˆÙ† ÙˆØ¶ÙˆØ­Ù‹Ø§ Ù‚Ø¨Ù„ Ø§Ù„Ø¯Ø®ÙˆÙ„.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "ØªØ±ÙƒØ² Ø§Ù„Ù…Ù†ØµØ© Ø¹Ù„Ù‰ Ø¯Ø¹Ù… Ø§Ù„Ù‚Ø±Ø§Ø± ÙˆØ¬ÙˆØ¯Ø© Ø§Ù„Ø¥Ø´Ø§Ø±Ø© ÙˆÙˆØ¶ÙˆØ­ Ø§Ù„Ø£Ù‡Ø¯Ø§Ù Ø¨Ø¯Ù„ Ø§Ù„ØªÙ†Ø¨ÙŠÙ‡Ø§Øª Ø§Ù„Ø¹Ø´ÙˆØ§Ø¦ÙŠØ©.",
      "A simple flow from website to Telegram to dashboard.": "Ø±Ø­Ù„Ø© Ø¨Ø³ÙŠØ·Ø© Ù…Ù† Ø§Ù„Ù…ÙˆÙ‚Ø¹ Ø¥Ù„Ù‰ ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… Ø«Ù… Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯.",
      "More than signals. A full AI trading workspace.": "Ø£ÙƒØ«Ø± Ù…Ù† Ø¥Ø´Ø§Ø±Ø§Øª. Ù…Ø³Ø§Ø­Ø© ØªØ¯Ø§ÙˆÙ„ ÙƒØ§Ù…Ù„Ø© Ù…Ø¯Ø¹ÙˆÙ…Ø© Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ.",
      "Rules, paper trading, AI optimization, strategy templates, exchanges, executions, academy, and platform tools.": "Ù‚ÙˆØ§Ø¹Ø¯ ØªØ¯Ø§ÙˆÙ„ØŒ ØªØ¬Ø±Ø¨Ø© ÙˆØ±Ù‚ÙŠØ©ØŒ ØªØ­Ø³ÙŠÙ†Ø§Øª Ø°ÙƒØ§Ø¡ Ø§ØµØ·Ù†Ø§Ø¹ÙŠØŒ Ù‚ÙˆØ§Ù„Ø¨ Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ§ØªØŒ Ù…Ù†ØµØ§ØªØŒ ØªÙ†ÙÙŠØ°ØŒ Ø£ÙƒØ§Ø¯ÙŠÙ…ÙŠØ©ØŒ ÙˆØ£Ø¯ÙˆØ§Øª Ù„Ù„Ù…Ù†ØµØ©.",
      "Built to feel like a trading automation platform, positioned around safer AI signal delivery.": "Ù…ØµÙ…Ù… Ù„ÙŠØ¨Ø¯Ùˆ ÙƒÙ…Ù†ØµØ© Ø£ØªÙ…ØªØ© ØªØ¯Ø§ÙˆÙ„ Ø§Ø­ØªØ±Ø§ÙÙŠØ© Ù…Ø¹ ØªØ±ÙƒÙŠØ² Ø¹Ù„Ù‰ ØªÙˆØµÙŠÙ„ Ø¥Ø´Ø§Ø±Ø§Øª AI Ø£ÙƒØ«Ø± Ø£Ù…Ø§Ù†Ù‹Ø§.",
      "Clear plans without renaming production plan IDs.": "Ø®Ø·Ø· ÙˆØ§Ø¶Ø­Ø© Ø¨Ø¯ÙˆÙ† ØªØºÙŠÙŠØ± Ù…Ø¹Ø±ÙØ§Øª Ø§Ù„Ø®Ø·Ø· Ø§Ù„Ø¥Ù†ØªØ§Ø¬ÙŠØ©.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Ø§Ø®ØªØ± Ø§Ù„Ø®Ø·Ø© Ø§Ù„Ù…Ù†Ø§Ø³Ø¨Ø© Ù„Ø§Ø³ØªØ®Ø¯Ø§Ù…Ùƒ. Ø§Ù„Ø¯ÙØ¹ Ø§Ù„ÙŠØ¯ÙˆÙŠ Ù…ØªØ§Ø­ Ø¯Ø§Ø¦Ù…Ù‹Ø§.",
      "Review examples before subscribing.": "Ø±Ø§Ø¬Ø¹ Ø§Ù„Ø£Ù…Ø«Ù„Ø© Ù‚Ø¨Ù„ Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ.",
      "Use the proof page and official bot check to verify what the platform shows. Avoid fake Telegram accounts and never trust guaranteed profit claims.": "Ø§Ø³ØªØ®Ø¯Ù… ØµÙØ­Ø© Ø§Ù„Ø¥Ø«Ø¨Ø§Øª ÙˆÙØ­Øµ Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ Ù„Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„Ù…Ù†ØµØ©. ØªØ¬Ù†Ø¨ Ø­Ø³Ø§Ø¨Ø§Øª ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… Ø§Ù„Ù…Ø²ÙŠÙØ© ÙˆÙ„Ø§ ØªØ«Ù‚ Ø¨Ø£ÙŠ ÙˆØ¹ÙˆØ¯ Ø±Ø¨Ø­ Ù…Ø¶Ù…ÙˆÙ†Ø©.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader Ø¨Ø±Ù†Ø§Ù…Ø¬ Ù„Ø¯Ø¹Ù… Ø§Ù„Ù‚Ø±Ø§Ø±. ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø¹Ù…Ù„Ø§Øª Ø§Ù„Ø±Ù‚Ù…ÙŠØ© Ø¹Ø§Ù„ÙŠ Ø§Ù„Ù…Ø®Ø§Ø·Ø±. Ø§Ù„Ø¥Ø´Ø§Ø±Ø§Øª ÙˆØ§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ ÙˆØªØ­Ù„ÙŠÙ„ Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ Ù„Ø§ ØªØ¶Ù…Ù† Ø§Ù„Ø±Ø¨Ø­. Ø£Ø¯ÙØ± Ø±Ø£Ø³ Ù…Ø§Ù„Ùƒ ÙˆØ§ØªØ®Ø° Ù‚Ø±Ø§Ø±Ùƒ Ø§Ù„Ù†Ù‡Ø§Ø¦ÙŠ Ø¨Ù†ÙØ³Ùƒ.",
      "Animated dashboard preview built around real product workflows.": "Ù…Ø¹Ø§ÙŠÙ†Ø© Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ Ù…ØªØ­Ø±ÙƒØ© Ù…Ø¨Ù†ÙŠØ© Ø¹Ù„Ù‰ ØªØ¯ÙÙ‚Ø§Øª Ø§Ù„Ù…Ù†ØªØ¬ Ø§Ù„Ø­Ù‚ÙŠÙ‚ÙŠØ©.",
      "No fake profit guarantees. The interface highlights plan status, Telegram linking, signal quality, and performance tracking.": "Ø¨Ø¯ÙˆÙ† ÙˆØ¹ÙˆØ¯ Ø£Ø±Ø¨Ø§Ø­ ÙˆÙ‡Ù…ÙŠØ©. Ø§Ù„ÙˆØ§Ø¬Ù‡Ø© ØªØ¹Ø±Ø¶ Ø­Ø§Ù„Ø© Ø§Ù„Ø®Ø·Ø©ØŒ Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…ØŒ Ø¬ÙˆØ¯Ø© Ø§Ù„Ø¥Ø´Ø§Ø±Ø§ØªØŒ ÙˆØªØªØ¨Ø¹ Ø§Ù„Ø£Ø¯Ø§Ø¡.",
      "Performance is displayed only when tracked data exists.": "ÙŠØªÙ… Ø¹Ø±Ø¶ Ø§Ù„Ø£Ø¯Ø§Ø¡ ÙÙ‚Ø· Ø¹Ù†Ø¯ ÙˆØ¬ÙˆØ¯ Ø¨ÙŠØ§Ù†Ø§Øª ØªØªØ¨Ø¹ Ø­Ù‚ÙŠÙ‚ÙŠØ©.",
      "Nexora avoids fake results. New accounts see clear empty states until real signals and closed outcomes are recorded.": "Nexora ÙŠØªØ¬Ù†Ø¨ Ø§Ù„Ù†ØªØ§Ø¦Ø¬ Ø§Ù„ÙˆÙ‡Ù…ÙŠØ©. Ø§Ù„Ø­Ø³Ø§Ø¨Ø§Øª Ø§Ù„Ø¬Ø¯ÙŠØ¯Ø© ØªØ±Ù‰ Ø­Ø§Ù„Ø§Øª ÙØ§Ø±ØºØ© ÙˆØ§Ø¶Ø­Ø© Ø­ØªÙ‰ ÙŠØªÙ… ØªØ³Ø¬ÙŠÙ„ Ø¥Ø´Ø§Ø±Ø§Øª ÙˆÙ†ØªØ§Ø¦Ø¬ Ù…ØºÙ„Ù‚Ø© Ø­Ù‚ÙŠÙ‚ÙŠØ©.",
      "Built with production safety in mind.": "Ù…ØµÙ…Ù… Ù…Ø¹ Ù…Ø±Ø§Ø¹Ø§Ø© Ø£Ù…Ø§Ù† Ø§Ù„Ø¥Ù†ØªØ§Ø¬.",
      "A clear path for buyers and operators.": "Ù…Ø³Ø§Ø± ÙˆØ§Ø¶Ø­ Ù„Ù„Ù…Ø´ØªØ±ÙŠÙ† ÙˆØ§Ù„Ù…Ø´ØºÙ„ÙŠÙ†.",
      "Use verified customer quotes when available.": "Ø§Ø³ØªØ®Ø¯Ù… Ø¢Ø±Ø§Ø¡ Ø¹Ù…Ù„Ø§Ø¡ Ù…ÙˆØ«Ù‚Ø© Ø¹Ù†Ø¯ ØªÙˆÙØ±Ù‡Ø§.",
      "Until real testimonials are approved, this section stays honest and product-focused.": "Ø­ØªÙ‰ ÙŠØªÙ… Ø§Ø¹ØªÙ…Ø§Ø¯ Ø´Ù‡Ø§Ø¯Ø§Øª Ø­Ù‚ÙŠÙ‚ÙŠØ©ØŒ ÙŠØ¸Ù„ Ù‡Ø°Ø§ Ø§Ù„Ù‚Ø³Ù… ØµØ§Ø¯Ù‚Ù‹Ø§ ÙˆÙ…Ø±ÙƒØ²Ù‹Ø§ Ø¹Ù„Ù‰ Ø§Ù„Ù…Ù†ØªØ¬.",
      "Common questions before subscribing.": "Ø£Ø³Ø¦Ù„Ø© Ø´Ø§Ø¦Ø¹Ø© Ù‚Ø¨Ù„ Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ.",
      "Does Nexora guarantee profit?": "Ù‡Ù„ ØªØ¶Ù…Ù† Nexora Ø§Ù„Ø±Ø¨Ø­ØŸ",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Ù„Ø§. ØªÙ‚Ø¯Ù… ØªØ­Ù„ÙŠÙ„ Ø³ÙˆÙ‚ Ù…Ø¯Ø¹ÙˆÙ… Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ ÙˆØªÙ†Ø¨ÙŠÙ‡Ø§Øª Ù…Ù†Ø¸Ù…Ø©. Ù†ØªØ§Ø¦Ø¬ Ø§Ù„ØªØ¯Ø§ÙˆÙ„ ØºÙŠØ± Ù…Ø¶Ù…ÙˆÙ†Ø©.",
      "How do I receive signals?": "ÙƒÙŠÙ Ø£Ø³ØªÙ‚Ø¨Ù„ Ø§Ù„Ø¥Ø´Ø§Ø±Ø§ØªØŸ",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Ø£Ù†Ø´Ø¦ Ø­Ø³Ø§Ø¨Ù‹Ø§ØŒ Ø§Ø±Ø¨Ø· Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ Ø¹Ù„Ù‰ ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…ØŒ ÙˆØ­Ø§ÙØ¸ Ø¹Ù„Ù‰ Ø§Ù„Ø§ØªØµØ§Ù„ Ù…Ù† Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Ø°ÙƒØ§Ø¡ Ø¥Ø´Ø§Ø±Ø§Øª ÙƒØ±ÙŠØ¨ØªÙˆ Ø§Ø­ØªØ±Ø§ÙÙŠ Ù…Ø¹ ØªÙˆØµÙŠÙ„ Ù…ÙØ¯Ø§Ø± Ø¨Ø§Ù„Ù…Ø®Ø§Ø·Ø±ØŒ Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…ØŒ ÙˆØ¯Ø§Ø´Ø¨ÙˆØ±Ø¯ Ù†Ø¸ÙŠÙ.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Ø£Ù†Ø´Ø¦ Ø­Ø³Ø§Ø¨Ùƒ Ù…Ø¨Ø§Ø´Ø±Ø©ØŒ Ø«Ù… Ø§Ø±Ø¨Ø· ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… Ù…Ù† Ø§Ù„Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ Ø£Ùˆ Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø±Ø³Ù…ÙŠ."
    },
    es: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plataforma de seÃ±ales cripto asistida por IA con alertas de Telegram gestionadas por riesgo y seguimiento en panel.",
      "AI crypto signal platform for serious traders": "Plataforma de seÃ±ales cripto con IA para traders serios",
      "Professional BTC/USDT trading terminal.": "Terminal profesional de trading BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vista completa de TradingView para contexto del grÃ¡fico, lectura de tendencia y revisiÃ³n del precio antes de abrir el panel.",
      "Built for traders who want clarity before entry.": "Creado para traders que quieren claridad antes de entrar.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "La plataforma prioriza soporte de decisiÃ³n, seÃ±ales mÃ¡s limpias y objetivos transparentes en lugar de alertas ruidosas.",
      "A simple flow from website to Telegram to dashboard.": "Un flujo simple del sitio web a Telegram y luego al panel.",
      "More than signals. A full AI trading workspace.": "MÃ¡s que seÃ±ales. Un espacio completo de trading con IA.",
      "Clear plans without renaming production plan IDs.": "Planes claros sin renombrar los IDs de producciÃ³n.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Elige el plan que se adapte a tu uso. El pago manual sigue disponible.",
      "Review examples before subscribing.": "Revisa ejemplos antes de suscribirte.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader es software de apoyo a decisiones. El trading cripto implica riesgo. Las seÃ±ales, paneles y anÃ¡lisis de IA no garantizan ganancias.",
      "Performance is displayed only when tracked data exists.": "El rendimiento solo se muestra cuando existen datos reales rastreados.",
      "Common questions before subscribing.": "Preguntas frecuentes antes de suscribirse.",
      "Does Nexora guarantee profit?": "Â¿Nexora garantiza ganancias?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "No. Proporciona anÃ¡lisis de mercado asistido por IA y alertas estructuradas. Los resultados nunca estÃ¡n garantizados.",
      "How do I receive signals?": "Â¿CÃ³mo recibo seÃ±ales?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Crea una cuenta, vincula el bot oficial de Telegram y mantenlo conectado desde tu panel.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Inteligencia premium de seÃ±ales cripto con entrega gestionada por riesgo, conexiÃ³n Telegram y panel limpio.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Crea tu cuenta directamente y luego vincula Telegram desde el panel o el bot oficial."
    },
    fr: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plateforme de signaux crypto assistÃ©e par IA avec alertes Telegram Ã  risque maÃ®trisÃ© et suivi dans le tableau de bord.",
      "AI crypto signal platform for serious traders": "Plateforme de signaux crypto IA pour traders sÃ©rieux",
      "Professional BTC/USDT trading terminal.": "Terminal de trading BTC/USDT professionnel.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vue TradingView pleine largeur pour analyser le graphique, la tendance et l'action des prix avant d'ouvrir le tableau de bord.",
      "Built for traders who want clarity before entry.": "ConÃ§u pour les traders qui veulent de la clartÃ© avant l'entrÃ©e.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "La plateforme privilÃ©gie l'aide Ã  la dÃ©cision, la qualitÃ© des signaux et des objectifs transparents plutÃ´t que des alertes bruyantes.",
      "A simple flow from website to Telegram to dashboard.": "Un parcours simple du site vers Telegram puis le tableau de bord.",
      "More than signals. A full AI trading workspace.": "Plus que des signaux. Un espace de trading IA complet.",
      "Clear plans without renaming production plan IDs.": "Des plans clairs sans renommer les IDs de production.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Choisissez le plan adaptÃ© Ã  votre usage. Le paiement manuel reste disponible.",
      "Review examples before subscribing.": "Consultez les exemples avant de vous abonner.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader est un logiciel d'aide Ã  la dÃ©cision. Le trading crypto est risquÃ©. Les signaux, tableaux de bord et analyses IA ne garantissent pas de profits.",
      "Performance is displayed only when tracked data exists.": "La performance s'affiche uniquement lorsque des donnÃ©es suivies existent.",
      "Common questions before subscribing.": "Questions frÃ©quentes avant l'abonnement.",
      "Does Nexora guarantee profit?": "Nexora garantit-il des profits ?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Non. Il fournit une analyse de marchÃ© assistÃ©e par IA et des alertes structurÃ©es. Les rÃ©sultats ne sont jamais garantis.",
      "How do I receive signals?": "Comment recevoir les signaux ?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "CrÃ©ez un compte, liez le bot Telegram officiel et gardez-le connectÃ© depuis votre tableau de bord.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Intelligence premium de signaux crypto avec livraison maÃ®trisÃ©e, connexion Telegram et tableau de bord clair.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "CrÃ©ez votre compte directement, puis liez Telegram depuis le tableau de bord ou le bot officiel."
    },
    de: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "KI-gestÃ¼tzte Krypto-Signalplattform mit risikogesteuerten Telegram-Alerts und Dashboard-Tracking.",
      "AI crypto signal platform for serious traders": "KI-Krypto-Signalplattform fÃ¼r ernsthafte Trader",
      "Professional BTC/USDT trading terminal.": "Professionelles BTC/USDT-Trading-Terminal.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "Vollbreite TradingView-Ansicht fÃ¼r Chart-Kontext, Trendanalyse und Price-Action-PrÃ¼fung vor dem Dashboard.",
      "Built for traders who want clarity before entry.": "FÃ¼r Trader gebaut, die vor dem Einstieg Klarheit wollen.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Die Plattform fokussiert Entscheidungshilfe, saubere SignalqualitÃ¤t und transparente Ziele statt lauter Alerts.",
      "A simple flow from website to Telegram to dashboard.": "Ein einfacher Ablauf von Website zu Telegram zum Dashboard.",
      "More than signals. A full AI trading workspace.": "Mehr als Signale. Ein kompletter KI-Trading-Arbeitsbereich.",
      "Clear plans without renaming production plan IDs.": "Klare PlÃ¤ne ohne Umbenennung produktiver Plan-IDs.",
      "Choose the plan that matches your usage. Manual payment stays available.": "WÃ¤hlen Sie den passenden Plan. Manuelle Zahlung bleibt verfÃ¼gbar.",
      "Review examples before subscribing.": "PrÃ¼fen Sie Beispiele vor dem Abonnieren.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader ist Entscheidungssoftware. Krypto-Trading ist riskant. Signale, Dashboards und KI-Analysen garantieren keine Gewinne.",
      "Performance is displayed only when tracked data exists.": "Performance wird nur angezeigt, wenn echte Tracking-Daten vorhanden sind.",
      "Common questions before subscribing.": "HÃ¤ufige Fragen vor dem Abo.",
      "Does Nexora guarantee profit?": "Garantiert Nexora Gewinn?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Nein. Es bietet KI-gestÃ¼tzte Marktanalyse und strukturierte Alerts. Ergebnisse sind nie garantiert.",
      "How do I receive signals?": "Wie erhalte ich Signale?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Konto erstellen, offiziellen Telegram-Bot verbinden und im Dashboard verbunden halten.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Premium-Krypto-Signalintelligenz mit risikogesteuerter Zustellung, Telegram-Verbindung und klarem Dashboard.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Erstellen Sie Ihr Konto direkt und verbinden Sie Telegram danach im Dashboard oder offiziellen Bot."
    },
    tr: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Risk yÃ¶netimli Telegram uyarÄ±larÄ± ve panel takibi olan yapay zekÃ¢ destekli kripto sinyal platformu.",
      "AI crypto signal platform for serious traders": "Ciddi yatÄ±rÄ±mcÄ±lar iÃ§in yapay zekÃ¢ kripto sinyal platformu",
      "Professional BTC/USDT trading terminal.": "Profesyonel BTC/USDT iÅŸlem terminali.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "KullanÄ±cÄ±lar panele girmeden Ã¶nce grafik baÄŸlamÄ±, trend ve fiyat hareketini incelemek iÃ§in tam geniÅŸlik TradingView gÃ¶rÃ¼nÃ¼mÃ¼.",
      "Built for traders who want clarity before entry.": "Ä°ÅŸleme girmeden Ã¶nce netlik isteyen traderlar iÃ§in tasarlandÄ±.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "Platform gÃ¼rÃ¼ltÃ¼lÃ¼ uyarÄ±lar yerine karar desteÄŸi, temiz sinyal kalitesi ve ÅŸeffaf hedeflere odaklanÄ±r.",
      "A simple flow from website to Telegram to dashboard.": "Web sitesinden Telegram'a ve ardÄ±ndan panele uzanan basit akÄ±ÅŸ.",
      "More than signals. A full AI trading workspace.": "Sinyallerden fazlasÄ±. Tam bir yapay zekÃ¢ iÅŸlem alanÄ±.",
      "Clear plans without renaming production plan IDs.": "Ãœretim plan kimliklerini deÄŸiÅŸtirmeden net planlar.",
      "Choose the plan that matches your usage. Manual payment stays available.": "KullanÄ±mÄ±nÄ±za uygun planÄ± seÃ§in. Manuel Ã¶deme kullanÄ±labilir kalÄ±r.",
      "Review examples before subscribing.": "Abone olmadan Ã¶nce Ã¶rnekleri inceleyin.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader karar destek yazÄ±lÄ±mÄ±dÄ±r. Kripto iÅŸlemleri risklidir. Sinyaller ve analizler kÃ¢r garantisi vermez.",
      "Performance is displayed only when tracked data exists.": "Performans yalnÄ±zca takip edilen gerÃ§ek veri varsa gÃ¶sterilir.",
      "Common questions before subscribing.": "Abonelik Ã¶ncesi sÄ±k sorular.",
      "Does Nexora guarantee profit?": "Nexora kÃ¢r garantisi verir mi?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "HayÄ±r. Yapay zekÃ¢ destekli piyasa analizi ve yapÄ±landÄ±rÄ±lmÄ±ÅŸ uyarÄ±lar sunar. SonuÃ§lar garanti deÄŸildir.",
      "How do I receive signals?": "Sinyalleri nasÄ±l alÄ±rÄ±m?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Hesap oluÅŸturun, resmi Telegram botunu baÄŸlayÄ±n ve panelden baÄŸlÄ± tutun.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Risk yÃ¶netimli gÃ¶nderim, Telegram baÄŸlantÄ±sÄ± ve temiz panel ile premium kripto sinyal zekÃ¢sÄ±.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "HesabÄ±nÄ±zÄ± doÄŸrudan oluÅŸturun, ardÄ±ndan panelden veya resmi bottan Telegram'Ä± baÄŸlayÄ±n."
    },
    pt: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "Plataforma de sinais cripto com IA, alertas Telegram com gestÃ£o de risco e acompanhamento no painel.",
      "AI crypto signal platform for serious traders": "Plataforma de sinais cripto com IA para traders sÃ©rios",
      "Professional BTC/USDT trading terminal.": "Terminal profissional de trading BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "VisÃ£o TradingView em largura total para contexto do grÃ¡fico, leitura de tendÃªncia e revisÃ£o do preÃ§o antes do painel.",
      "Built for traders who want clarity before entry.": "Criado para traders que querem clareza antes da entrada.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "A plataforma foca em apoio Ã  decisÃ£o, qualidade de sinal e alvos transparentes em vez de alertas ruidosos.",
      "A simple flow from website to Telegram to dashboard.": "Um fluxo simples do site para o Telegram e depois para o painel.",
      "More than signals. A full AI trading workspace.": "Mais que sinais. Um espaÃ§o completo de trading com IA.",
      "Clear plans without renaming production plan IDs.": "Planos claros sem renomear IDs de produÃ§Ã£o.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Escolha o plano que combina com seu uso. Pagamento manual continua disponÃ­vel.",
      "Review examples before subscribing.": "Revise exemplos antes de assinar.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader Ã© software de apoio Ã  decisÃ£o. Trading cripto Ã© arriscado. Sinais e anÃ¡lises nÃ£o garantem lucro.",
      "Performance is displayed only when tracked data exists.": "O desempenho sÃ³ aparece quando existem dados reais rastreados.",
      "Common questions before subscribing.": "Perguntas comuns antes da assinatura.",
      "Does Nexora guarantee profit?": "A Nexora garante lucro?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "NÃ£o. Ela fornece anÃ¡lise de mercado com IA e alertas estruturados. Resultados nunca sÃ£o garantidos.",
      "How do I receive signals?": "Como recebo sinais?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Crie uma conta, conecte o bot oficial do Telegram e mantenha-o conectado no painel.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "InteligÃªncia premium de sinais cripto com entrega gerida por risco, Telegram e painel limpo.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Crie sua conta diretamente e depois conecte o Telegram pelo painel ou bot oficial."
    },
    ru: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "ÐŸÐ»Ð°Ñ‚Ñ„Ð¾Ñ€Ð¼Ð° ÐºÑ€Ð¸Ð¿Ñ‚Ð¾-ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² Ñ Ð˜Ð˜, Telegram-ÑƒÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸ÑÐ¼Ð¸ Ñ ÐºÐ¾Ð½Ñ‚Ñ€Ð¾Ð»ÐµÐ¼ Ñ€Ð¸ÑÐºÐ° Ð¸ Ð¾Ñ‚ÑÐ»ÐµÐ¶Ð¸Ð²Ð°Ð½Ð¸ÐµÐ¼ Ð² Ð¿Ð°Ð½ÐµÐ»Ð¸.",
      "AI crypto signal platform for serious traders": "ÐŸÐ»Ð°Ñ‚Ñ„Ð¾Ñ€Ð¼Ð° Ð˜Ð˜ ÐºÑ€Ð¸Ð¿Ñ‚Ð¾-ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² Ð´Ð»Ñ ÑÐµÑ€ÑŒÐµÐ·Ð½Ñ‹Ñ… Ñ‚Ñ€ÐµÐ¹Ð´ÐµÑ€Ð¾Ð²",
      "Professional BTC/USDT trading terminal.": "ÐŸÑ€Ð¾Ñ„ÐµÑÑÐ¸Ð¾Ð½Ð°Ð»ÑŒÐ½Ñ‹Ð¹ Ñ‚Ð¾Ñ€Ð³Ð¾Ð²Ñ‹Ð¹ Ñ‚ÐµÑ€Ð¼Ð¸Ð½Ð°Ð» BTC/USDT.",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "ÐŸÐ¾Ð»Ð½Ð¾ÑˆÐ¸Ñ€Ð¸Ð½Ð½Ñ‹Ð¹ TradingView Ð´Ð»Ñ Ð°Ð½Ð°Ð»Ð¸Ð·Ð° Ð³Ñ€Ð°Ñ„Ð¸ÐºÐ°, Ñ‚Ñ€ÐµÐ½Ð´Ð° Ð¸ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸Ñ Ñ†ÐµÐ½Ñ‹ Ð¿ÐµÑ€ÐµÐ´ Ð¾Ñ‚ÐºÑ€Ñ‹Ñ‚Ð¸ÐµÐ¼ Ð¿Ð°Ð½ÐµÐ»Ð¸.",
      "Built for traders who want clarity before entry.": "Ð¡Ð¾Ð·Ð´Ð°Ð½Ð¾ Ð´Ð»Ñ Ñ‚Ñ€ÐµÐ¹Ð´ÐµÑ€Ð¾Ð², ÐºÐ¾Ñ‚Ð¾Ñ€Ñ‹Ð¼ Ð½ÑƒÐ¶Ð½Ð° ÑÑÐ½Ð¾ÑÑ‚ÑŒ Ð¿ÐµÑ€ÐµÐ´ Ð²Ñ…Ð¾Ð´Ð¾Ð¼.",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "ÐŸÐ»Ð°Ñ‚Ñ„Ð¾Ñ€Ð¼Ð° Ð´ÐµÐ»Ð°ÐµÑ‚ Ð°ÐºÑ†ÐµÐ½Ñ‚ Ð½Ð° Ð¿Ð¾Ð´Ð´ÐµÑ€Ð¶ÐºÐµ Ñ€ÐµÑˆÐµÐ½Ð¸Ð¹, ÐºÐ°Ñ‡ÐµÑÑ‚Ð²Ðµ ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² Ð¸ Ð¿Ñ€Ð¾Ð·Ñ€Ð°Ñ‡Ð½Ñ‹Ñ… Ñ†ÐµÐ»ÑÑ… Ð²Ð¼ÐµÑÑ‚Ð¾ ÑˆÑƒÐ¼Ð½Ñ‹Ñ… ÑƒÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ð¹.",
      "A simple flow from website to Telegram to dashboard.": "ÐŸÑ€Ð¾ÑÑ‚Ð¾Ð¹ Ð¿ÑƒÑ‚ÑŒ: ÑÐ°Ð¹Ñ‚, Telegram, Ð·Ð°Ñ‚ÐµÐ¼ Ð¿Ð°Ð½ÐµÐ»ÑŒ.",
      "More than signals. A full AI trading workspace.": "Ð‘Ð¾Ð»ÑŒÑˆÐµ, Ñ‡ÐµÐ¼ ÑÐ¸Ð³Ð½Ð°Ð»Ñ‹. ÐŸÐ¾Ð»Ð½Ð¾Ðµ Ñ€Ð°Ð±Ð¾Ñ‡ÐµÐµ Ð¿Ñ€Ð¾ÑÑ‚Ñ€Ð°Ð½ÑÑ‚Ð²Ð¾ Ñ‚Ñ€ÐµÐ¹Ð´Ð¸Ð½Ð³Ð° Ñ Ð˜Ð˜.",
      "Clear plans without renaming production plan IDs.": "ÐŸÐ¾Ð½ÑÑ‚Ð½Ñ‹Ðµ Ð¿Ð»Ð°Ð½Ñ‹ Ð±ÐµÐ· Ð¿ÐµÑ€ÐµÐ¸Ð¼ÐµÐ½Ð¾Ð²Ð°Ð½Ð¸Ñ production ID.",
      "Choose the plan that matches your usage. Manual payment stays available.": "Ð’Ñ‹Ð±ÐµÑ€Ð¸Ñ‚Ðµ Ð¿Ð»Ð°Ð½ Ð¿Ð¾Ð´ Ð²Ð°ÑˆÐ¸ Ð·Ð°Ð´Ð°Ñ‡Ð¸. Ð ÑƒÑ‡Ð½Ð°Ñ Ð¾Ð¿Ð»Ð°Ñ‚Ð° Ð´Ð¾ÑÑ‚ÑƒÐ¿Ð½Ð°.",
      "Review examples before subscribing.": "ÐŸÐ¾ÑÐ¼Ð¾Ñ‚Ñ€Ð¸Ñ‚Ðµ Ð¿Ñ€Ð¸Ð¼ÐµÑ€Ñ‹ Ð¿ÐµÑ€ÐµÐ´ Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐ¾Ð¹.",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader â€” ÐŸÐž Ð´Ð»Ñ Ð¿Ð¾Ð´Ð´ÐµÑ€Ð¶ÐºÐ¸ Ñ€ÐµÑˆÐµÐ½Ð¸Ð¹. ÐšÑ€Ð¸Ð¿Ñ‚Ð¾Ñ‚Ñ€ÐµÐ¹Ð´Ð¸Ð½Ð³ Ñ€Ð¸ÑÐºÐ¾Ð²Ð°Ð½. Ð¡Ð¸Ð³Ð½Ð°Ð»Ñ‹ Ð¸ Ð˜Ð˜-Ð°Ð½Ð°Ð»Ð¸Ð· Ð½Ðµ Ð³Ð°Ñ€Ð°Ð½Ñ‚Ð¸Ñ€ÑƒÑŽÑ‚ Ð¿Ñ€Ð¸Ð±Ñ‹Ð»ÑŒ.",
      "Performance is displayed only when tracked data exists.": "ÐŸÐ¾ÐºÐ°Ð·Ð°Ñ‚ÐµÐ»Ð¸ Ð¾Ñ‚Ð¾Ð±Ñ€Ð°Ð¶Ð°ÑŽÑ‚ÑÑ Ñ‚Ð¾Ð»ÑŒÐºÐ¾ Ð¿Ñ€Ð¸ Ð½Ð°Ð»Ð¸Ñ‡Ð¸Ð¸ Ñ€ÐµÐ°Ð»ÑŒÐ½Ñ‹Ñ… Ð´Ð°Ð½Ð½Ñ‹Ñ….",
      "Common questions before subscribing.": "Ð§Ð°ÑÑ‚Ñ‹Ðµ Ð²Ð¾Ð¿Ñ€Ð¾ÑÑ‹ Ð¿ÐµÑ€ÐµÐ´ Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐ¾Ð¹.",
      "Does Nexora guarantee profit?": "Nexora Ð³Ð°Ñ€Ð°Ð½Ñ‚Ð¸Ñ€ÑƒÐµÑ‚ Ð¿Ñ€Ð¸Ð±Ñ‹Ð»ÑŒ?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "ÐÐµÑ‚. ÐžÐ½Ð° Ð´Ð°ÐµÑ‚ Ð˜Ð˜-Ð°Ð½Ð°Ð»Ð¸Ð· Ñ€Ñ‹Ð½ÐºÐ° Ð¸ ÑÑ‚Ñ€ÑƒÐºÑ‚ÑƒÑ€Ð¸Ñ€Ð¾Ð²Ð°Ð½Ð½Ñ‹Ðµ ÑƒÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ñ. Ð ÐµÐ·ÑƒÐ»ÑŒÑ‚Ð°Ñ‚Ñ‹ Ð½Ðµ Ð³Ð°Ñ€Ð°Ð½Ñ‚Ð¸Ñ€ÑƒÑŽÑ‚ÑÑ.",
      "How do I receive signals?": "ÐšÐ°Ðº Ð¿Ð¾Ð»ÑƒÑ‡Ð°Ñ‚ÑŒ ÑÐ¸Ð³Ð½Ð°Ð»Ñ‹?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Ð¡Ð¾Ð·Ð´Ð°Ð¹Ñ‚Ðµ Ð°ÐºÐºÐ°ÑƒÐ½Ñ‚, Ð¿Ð¾Ð´ÐºÐ»ÑŽÑ‡Ð¸Ñ‚Ðµ Ð¾Ñ„Ð¸Ñ†Ð¸Ð°Ð»ÑŒÐ½Ñ‹Ð¹ Telegram-Ð±Ð¾Ñ‚ Ð¸ Ð´ÐµÑ€Ð¶Ð¸Ñ‚Ðµ ÐµÐ³Ð¾ Ð¿Ð¾Ð´ÐºÐ»ÑŽÑ‡ÐµÐ½Ð½Ñ‹Ð¼ Ð² Ð¿Ð°Ð½ÐµÐ»Ð¸.",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "ÐŸÑ€ÐµÐ¼Ð¸Ð°Ð»ÑŒÐ½Ð°Ñ Ð°Ð½Ð°Ð»Ð¸Ñ‚Ð¸ÐºÐ° ÐºÑ€Ð¸Ð¿Ñ‚Ð¾-ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² Ñ ÐºÐ¾Ð½Ñ‚Ñ€Ð¾Ð»ÐµÐ¼ Ñ€Ð¸ÑÐºÐ°, Telegram Ð¸ ÑƒÐ´Ð¾Ð±Ð½Ð¾Ð¹ Ð¿Ð°Ð½ÐµÐ»ÑŒÑŽ.",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Ð¡Ð¾Ð·Ð´Ð°Ð¹Ñ‚Ðµ Ð°ÐºÐºÐ°ÑƒÐ½Ñ‚, Ð·Ð°Ñ‚ÐµÐ¼ Ð¿Ð¾Ð´ÐºÐ»ÑŽÑ‡Ð¸Ñ‚Ðµ Telegram Ñ‡ÐµÑ€ÐµÐ· Ð¿Ð°Ð½ÐµÐ»ÑŒ Ð¸Ð»Ð¸ Ð¾Ñ„Ð¸Ñ†Ð¸Ð°Ð»ÑŒÐ½Ñ‹Ð¹ Ð±Ð¾Ñ‚."
    },
    zh: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "ç”± AI è¾…åŠ©çš„åŠ å¯†ä¿¡å·å¹³å°ï¼Œæä¾›é£Žé™©ç®¡ç†çš„ Telegram æé†’å’Œä»ªè¡¨ç›˜è·Ÿè¸ªã€‚",
      "AI crypto signal platform for serious traders": "é¢å‘ä¸“ä¸šäº¤æ˜“è€…çš„ AI åŠ å¯†ä¿¡å·å¹³å°",
      "Professional BTC/USDT trading terminal.": "ä¸“ä¸š BTC/USDT äº¤æ˜“ç»ˆç«¯ã€‚",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "å…¨å®½ TradingView å¸‚åœºè§†å›¾ï¼Œç”¨äºŽåœ¨è¿›å…¥ä»ªè¡¨ç›˜å‰æŸ¥çœ‹å›¾è¡¨ã€è¶‹åŠ¿å’Œä»·æ ¼è¡Œä¸ºã€‚",
      "Built for traders who want clarity before entry.": "ä¸ºå¸Œæœ›åœ¨å…¥åœºå‰èŽ·å¾—æ¸…æ™°åˆ¤æ–­çš„äº¤æ˜“è€…æ‰“é€ ã€‚",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "å¹³å°ä¸“æ³¨äºŽå†³ç­–æ”¯æŒã€æ›´å¹²å‡€çš„ä¿¡å·è´¨é‡å’Œé€æ˜Žç›®æ ‡ï¼Œè€Œä¸æ˜¯å™ªéŸ³æé†’ã€‚",
      "A simple flow from website to Telegram to dashboard.": "ä»Žç½‘ç«™åˆ° Telegram å†åˆ°ä»ªè¡¨ç›˜çš„ç®€å•æµç¨‹ã€‚",
      "More than signals. A full AI trading workspace.": "ä¸åªæ˜¯ä¿¡å·ï¼Œè€Œæ˜¯å®Œæ•´çš„ AI äº¤æ˜“å·¥ä½œåŒºã€‚",
      "Clear plans without renaming production plan IDs.": "æ¸…æ™°å¥—é¤ï¼Œä¸æ”¹å˜ç”Ÿäº§è®¡åˆ’ IDã€‚",
      "Choose the plan that matches your usage. Manual payment stays available.": "é€‰æ‹©é€‚åˆä½ ä½¿ç”¨æ–¹å¼çš„å¥—é¤ã€‚ä»æ”¯æŒæ‰‹åŠ¨ä»˜æ¬¾ã€‚",
      "Review examples before subscribing.": "è®¢é˜…å‰å…ˆæŸ¥çœ‹ç¤ºä¾‹ã€‚",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader æ˜¯å†³ç­–è¾…åŠ©è½¯ä»¶ã€‚åŠ å¯†äº¤æ˜“æœ‰é£Žé™©ï¼Œä¿¡å·ã€ä»ªè¡¨ç›˜å’Œ AI åˆ†æžä¸ä¿è¯ç›ˆåˆ©ã€‚",
      "Performance is displayed only when tracked data exists.": "åªæœ‰å­˜åœ¨çœŸå®žè·Ÿè¸ªæ•°æ®æ—¶æ‰æ˜¾ç¤ºè¡¨çŽ°ã€‚",
      "Common questions before subscribing.": "è®¢é˜…å‰å¸¸è§é—®é¢˜ã€‚",
      "Does Nexora guarantee profit?": "Nexora ä¿è¯ç›ˆåˆ©å—ï¼Ÿ",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "ä¸ä¿è¯ã€‚å®ƒæä¾› AI è¾…åŠ©å¸‚åœºåˆ†æžå’Œç»“æž„åŒ–æé†’ï¼Œäº¤æ˜“ç»“æžœæ°¸è¿œæ— æ³•ä¿è¯ã€‚",
      "How do I receive signals?": "å¦‚ä½•æŽ¥æ”¶ä¿¡å·ï¼Ÿ",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "åˆ›å»ºè´¦æˆ·ï¼Œç»‘å®šå®˜æ–¹ Telegram æœºå™¨äººï¼Œå¹¶åœ¨ä»ªè¡¨ç›˜ä¿æŒè¿žæŽ¥ã€‚",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "é«˜çº§åŠ å¯†ä¿¡å·æ™ºèƒ½ï¼Œæ”¯æŒé£Žé™©ç®¡ç†æŠ•é€’ã€Telegram è¿žæŽ¥å’Œæ¸…æ™°ä»ªè¡¨ç›˜ã€‚",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "ç›´æŽ¥åˆ›å»ºè´¦æˆ·ï¼Œç„¶åŽä»Žä»ªè¡¨ç›˜æˆ–å®˜æ–¹æœºå™¨äººç»‘å®š Telegramã€‚"
    },
    hi: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "AI-à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾ à¤µà¤¾à¤²à¥€ à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿà¥‹ à¤¸à¤¿à¤—à¥à¤¨à¤² à¤ªà¥à¤²à¥‡à¤Ÿà¤«à¥‰à¤°à¥à¤®, à¤œà¥‹à¤–à¤¿à¤®-à¤ªà¥à¤°à¤¬à¤‚à¤§à¤¿à¤¤ Telegram à¤…à¤²à¤°à¥à¤Ÿ à¤”à¤° à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤Ÿà¥à¤°à¥ˆà¤•à¤¿à¤‚à¤— à¤•à¥‡ à¤¸à¤¾à¤¥à¥¤",
      "AI crypto signal platform for serious traders": "à¤—à¤‚à¤­à¥€à¤° à¤Ÿà¥à¤°à¥‡à¤¡à¤°à¥‹à¤‚ à¤•à¥‡ à¤²à¤¿à¤ AI à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿà¥‹ à¤¸à¤¿à¤—à¥à¤¨à¤² à¤ªà¥à¤²à¥‡à¤Ÿà¤«à¥‰à¤°à¥à¤®",
      "Professional BTC/USDT trading terminal.": "à¤ªà¥à¤°à¥‹à¤«à¥‡à¤¶à¤¨à¤² BTC/USDT à¤Ÿà¥à¤°à¥‡à¤¡à¤¿à¤‚à¤— à¤Ÿà¤°à¥à¤®à¤¿à¤¨à¤²à¥¤",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤–à¥‹à¤²à¤¨à¥‡ à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ à¤šà¤¾à¤°à¥à¤Ÿ, à¤Ÿà¥à¤°à¥‡à¤‚à¤¡ à¤”à¤° à¤ªà¥à¤°à¤¾à¤‡à¤¸ à¤à¤•à¥à¤¶à¤¨ à¤¦à¥‡à¤–à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ à¤«à¥à¤²-à¤µà¤¿à¤¥ TradingView à¤µà¥à¤¯à¥‚à¥¤",
      "Built for traders who want clarity before entry.": "à¤‰à¤¨ à¤Ÿà¥à¤°à¥‡à¤¡à¤°à¥‹à¤‚ à¤•à¥‡ à¤²à¤¿à¤ à¤¬à¤¨à¤¾à¤¯à¤¾ à¤—à¤¯à¤¾ à¤œà¥‹ à¤à¤‚à¤Ÿà¥à¤°à¥€ à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ à¤¸à¥à¤ªà¤·à¥à¤Ÿà¤¤à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "à¤ªà¥à¤²à¥‡à¤Ÿà¤«à¥‰à¤°à¥à¤® à¤¶à¥‹à¤° à¤µà¤¾à¤²à¥‡ à¤…à¤²à¤°à¥à¤Ÿ à¤•à¥€ à¤œà¤—à¤¹ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾, à¤¬à¥‡à¤¹à¤¤à¤° à¤¸à¤¿à¤—à¥à¤¨à¤² à¤—à¥à¤£à¤µà¤¤à¥à¤¤à¤¾ à¤”à¤° à¤¸à¤¾à¤« à¤²à¤•à¥à¤·à¥à¤¯à¥‹à¤‚ à¤ªà¤° à¤•à¥‡à¤‚à¤¦à¥à¤°à¤¿à¤¤ à¤¹à¥ˆà¥¤",
      "A simple flow from website to Telegram to dashboard.": "à¤µà¥‡à¤¬à¤¸à¤¾à¤‡à¤Ÿ à¤¸à¥‡ Telegram à¤”à¤° à¤«à¤¿à¤° à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤¤à¤• à¤¸à¤°à¤² à¤ªà¥à¤°à¤µà¤¾à¤¹à¥¤",
      "More than signals. A full AI trading workspace.": "à¤¸à¤¿à¤—à¥à¤¨à¤² à¤¸à¥‡ à¤…à¤§à¤¿à¤•à¥¤ à¤ªà¥‚à¤°à¤¾ AI à¤Ÿà¥à¤°à¥‡à¤¡à¤¿à¤‚à¤— à¤µà¤°à¥à¤•à¤¸à¥à¤ªà¥‡à¤¸à¥¤",
      "Clear plans without renaming production plan IDs.": "à¤ªà¥à¤°à¥‹à¤¡à¤•à¥à¤¶à¤¨ à¤ªà¥à¤²à¤¾à¤¨ IDs à¤¬à¤¦à¤²à¥‡ à¤¬à¤¿à¤¨à¤¾ à¤¸à¤¾à¤« à¤ªà¥à¤²à¤¾à¤¨à¥¤",
      "Choose the plan that matches your usage. Manual payment stays available.": "à¤…à¤ªà¤¨à¥‡ à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¥‡ à¤…à¤¨à¥à¤¸à¤¾à¤° à¤ªà¥à¤²à¤¾à¤¨ à¤šà¥à¤¨à¥‡à¤‚à¥¤ à¤®à¥ˆà¤¨à¥à¤…à¤² à¤ªà¥‡à¤®à¥‡à¤‚à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
      "Review examples before subscribing.": "à¤¸à¤¬à¥à¤¸à¤•à¥à¤°à¤¾à¤‡à¤¬ à¤•à¤°à¤¨à¥‡ à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ à¤‰à¤¦à¤¾à¤¹à¤°à¤£ à¤¦à¥‡à¤–à¥‡à¤‚à¥¤",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader à¤¨à¤¿à¤°à¥à¤£à¤¯-à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾ à¤¸à¥‰à¤«à¥à¤Ÿà¤µà¥‡à¤¯à¤° à¤¹à¥ˆà¥¤ à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿà¥‹ à¤Ÿà¥à¤°à¥‡à¤¡à¤¿à¤‚à¤— à¤œà¥‹à¤–à¤¿à¤®à¤ªà¥‚à¤°à¥à¤£ à¤¹à¥ˆà¥¤ à¤¸à¤¿à¤—à¥à¤¨à¤² à¤”à¤° AI à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£ à¤²à¤¾à¤­ à¤•à¥€ à¤—à¤¾à¤°à¤‚à¤Ÿà¥€ à¤¨à¤¹à¥€à¤‚ à¤¦à¥‡à¤¤à¥‡à¥¤",
      "Performance is displayed only when tracked data exists.": "à¤ªà¥à¤°à¤¦à¤°à¥à¤¶à¤¨ à¤¤à¤­à¥€ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ à¤œà¤¬ à¤µà¤¾à¤¸à¥à¤¤à¤µà¤¿à¤• à¤Ÿà¥à¤°à¥ˆà¤• à¤¡à¥‡à¤Ÿà¤¾ à¤®à¥Œà¤œà¥‚à¤¦ à¤¹à¥‹à¥¤",
      "Common questions before subscribing.": "à¤¸à¤¬à¥à¤¸à¤•à¥à¤°à¤¿à¤ªà¥à¤¶à¤¨ à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ à¤¸à¤¾à¤®à¤¾à¤¨à¥à¤¯ à¤ªà¥à¤°à¤¶à¥à¤¨à¥¤",
      "Does Nexora guarantee profit?": "à¤•à¥à¤¯à¤¾ Nexora à¤²à¤¾à¤­ à¤•à¥€ à¤—à¤¾à¤°à¤‚à¤Ÿà¥€ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ?",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "à¤¨à¤¹à¥€à¤‚à¥¤ à¤¯à¤¹ AI-à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾ à¤µà¤¾à¤²à¤¾ à¤®à¤¾à¤°à¥à¤•à¥‡à¤Ÿ à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£ à¤”à¤° à¤¸à¤‚à¤°à¤šà¤¿à¤¤ à¤…à¤²à¤°à¥à¤Ÿ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤ªà¤°à¤¿à¤£à¤¾à¤®à¥‹à¤‚ à¤•à¥€ à¤—à¤¾à¤°à¤‚à¤Ÿà¥€ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹à¤¤à¥€à¥¤",
      "How do I receive signals?": "à¤®à¥à¤à¥‡ à¤¸à¤¿à¤—à¥à¤¨à¤² à¤•à¥ˆà¤¸à¥‡ à¤®à¤¿à¤²à¥‡à¤‚à¤—à¥‡?",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "à¤–à¤¾à¤¤à¤¾ à¤¬à¤¨à¤¾à¤à¤‚, à¤†à¤§à¤¿à¤•à¤¾à¤°à¤¿à¤• Telegram bot à¤²à¤¿à¤‚à¤• à¤•à¤°à¥‡à¤‚ à¤”à¤° à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤¸à¥‡ à¤•à¤¨à¥‡à¤•à¥à¤Ÿ à¤°à¤–à¥‡à¤‚à¥¤",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "à¤œà¥‹à¤–à¤¿à¤®-à¤ªà¥à¤°à¤¬à¤‚à¤§à¤¿à¤¤ à¤¡à¤¿à¤²à¥€à¤µà¤°à¥€, Telegram à¤•à¤¨à¥‡à¤•à¥à¤¶à¤¨ à¤”à¤° à¤¸à¤¾à¤« à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤•à¥‡ à¤¸à¤¾à¤¥ à¤ªà¥à¤°à¥€à¤®à¤¿à¤¯à¤® à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿà¥‹ à¤¸à¤¿à¤—à¥à¤¨à¤² à¤‡à¤‚à¤Ÿà¥‡à¤²à¤¿à¤œà¥‡à¤‚à¤¸à¥¤",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "à¤¸à¥€à¤§à¥‡ à¤–à¤¾à¤¤à¤¾ à¤¬à¤¨à¤¾à¤à¤‚, à¤«à¤¿à¤° à¤¡à¥ˆà¤¶à¤¬à¥‹à¤°à¥à¤¡ à¤¯à¤¾ à¤†à¤§à¤¿à¤•à¤¾à¤°à¤¿à¤• bot à¤¸à¥‡ Telegram à¤²à¤¿à¤‚à¤• à¤•à¤°à¥‡à¤‚à¥¤"
    },
    ur: {
      "AI-assisted crypto signal platform with risk-managed Telegram alerts and dashboard tracking.": "AI Ú©ÛŒ Ù…Ø¯Ø¯ Ø³Û’ Ú©Ø±Ù¾Ù¹Ùˆ Ø³Ú¯Ù†Ù„ Ù¾Ù„ÛŒÙ¹ ÙØ§Ø±Ù…ØŒ Ø±Ø³Ú© Ù…ÛŒÙ†Ø¬Úˆ Telegram Ø§Ù„Ø±Ù¹Ø³ Ø§ÙˆØ± ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ Ù¹Ø±ÛŒÚ©Ù†Ú¯ Ú©Û’ Ø³Ø§ØªÚ¾Û”",
      "AI crypto signal platform for serious traders": "Ø³Ù†Ø¬ÛŒØ¯Û Ù¹Ø±ÛŒÚˆØ±Ø² Ú©Û’ Ù„ÛŒÛ’ AI Ú©Ø±Ù¾Ù¹Ùˆ Ø³Ú¯Ù†Ù„ Ù¾Ù„ÛŒÙ¹ ÙØ§Ø±Ù…",
      "Professional BTC/USDT trading terminal.": "Ù¾Ø±ÙˆÙÛŒØ´Ù†Ù„ BTC/USDT Ù¹Ø±ÛŒÚˆÙ†Ú¯ Ù¹Ø±Ù…ÛŒÙ†Ù„Û”",
      "Full-width TradingView market view for chart context, trend reading, and price action review before users open the dashboard.": "ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ Ú©Ú¾ÙˆÙ„Ù†Û’ Ø³Û’ Ù¾ÛÙ„Û’ Ú†Ø§Ø±Ù¹ØŒ Ù¹Ø±ÛŒÙ†Úˆ Ø§ÙˆØ± Ù¾Ø±Ø§Ø¦Ø³ Ø§ÛŒÚ©Ø´Ù† Ú©Û’ Ù„ÛŒÛ’ Ù…Ú©Ù…Ù„ TradingView Ù…Ø§Ø±Ú©ÛŒÙ¹ ÙˆÛŒÙˆÛ”",
      "Built for traders who want clarity before entry.": "Ø§Ù† Ù¹Ø±ÛŒÚˆØ±Ø² Ú©Û’ Ù„ÛŒÛ’ Ø¬Ùˆ Ø§Ù†Ù¹Ø±ÛŒ Ø³Û’ Ù¾ÛÙ„Û’ ÙˆØ§Ø¶Ø­ ÙÛŒØµÙ„Û Ú†Ø§ÛØªÛ’ ÛÛŒÚºÛ”",
      "The platform focuses on decision support, cleaner signal quality, and transparent targets instead of noisy alerts.": "ÛŒÛ Ù¾Ù„ÛŒÙ¹ ÙØ§Ø±Ù… Ø´ÙˆØ± ÙˆØ§Ù„Û’ Ø§Ù„Ø±Ù¹Ø³ Ú©Û’ Ø¨Ø¬Ø§Ø¦Û’ ÙÛŒØµÙ„Û Ø³Ø§Ø²ÛŒØŒ Ø¨ÛØªØ± Ø³Ú¯Ù†Ù„ Ú©ÙˆØ§Ù„Ù¹ÛŒ Ø§ÙˆØ± ÙˆØ§Ø¶Ø­ Ø§ÛØ¯Ø§Ù Ù¾Ø± ØªÙˆØ¬Û Ø¯ÛŒØªØ§ ÛÛ’Û”",
      "A simple flow from website to Telegram to dashboard.": "ÙˆÛŒØ¨ Ø³Ø§Ø¦Ù¹ Ø³Û’ Telegram Ø§ÙˆØ± Ù¾Ú¾Ø± ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ ØªÚ© Ø¢Ø³Ø§Ù† ÙÙ„ÙˆÛ”",
      "More than signals. A full AI trading workspace.": "ØµØ±Ù Ø³Ú¯Ù†Ù„Ø² Ù†ÛÛŒÚºØŒ Ù…Ú©Ù…Ù„ AI Ù¹Ø±ÛŒÚˆÙ†Ú¯ ÙˆØ±Ú© Ø§Ø³Ù¾ÛŒØ³Û”",
      "Clear plans without renaming production plan IDs.": "Ù¾Ø±ÙˆÚˆÚ©Ø´Ù† Ù¾Ù„Ø§Ù† IDs Ø¨Ø¯Ù„Û’ Ø¨ØºÛŒØ± ÙˆØ§Ø¶Ø­ Ù¾Ù„Ø§Ù†Ø²Û”",
      "Choose the plan that matches your usage. Manual payment stays available.": "Ø§Ù¾Ù†Û’ Ø§Ø³ØªØ¹Ù…Ø§Ù„ Ú©Û’ Ù…Ø·Ø§Ø¨Ù‚ Ù¾Ù„Ø§Ù† Ù…Ù†ØªØ®Ø¨ Ú©Ø±ÛŒÚºÛ” Ø¯Ø³ØªÛŒ Ø§Ø¯Ø§Ø¦ÛŒÚ¯ÛŒ Ø¯Ø³ØªÛŒØ§Ø¨ Ø±ÛØªÛŒ ÛÛ’Û”",
      "Review examples before subscribing.": "Ø³Ø¨Ø³Ú©Ø±Ø§Ø¦Ø¨ Ú©Ø±Ù†Û’ Ø³Û’ Ù¾ÛÙ„Û’ Ù…Ø«Ø§Ù„ÛŒÚº Ø¯ÛŒÚ©Ú¾ÛŒÚºÛ”",
      "Nexora AI Trader is decision-support software. Crypto trading is risky. Signals, dashboards, and AI analysis do not guarantee profits. Always manage capital and make your own final decision.": "Nexora AI Trader ÙÛŒØµÙ„Û Ø³Ø§Ø²ÛŒ Ù…ÛŒÚº Ù…Ø¯Ø¯ Ø¯ÛŒÙ†Û’ ÙˆØ§Ù„Ø§ Ø³Ø§ÙÙ¹ ÙˆÛŒØ¦Ø± ÛÛ’Û” Ú©Ø±Ù¾Ù¹Ùˆ Ù¹Ø±ÛŒÚˆÙ†Ú¯ Ø®Ø·Ø±Ù†Ø§Ú© ÛÛ’Û” Ø³Ú¯Ù†Ù„Ø² Ø§ÙˆØ± AI ØªØ¬Ø²ÛŒÛ Ù…Ù†Ø§ÙØ¹ Ú©ÛŒ Ø¶Ù…Ø§Ù†Øª Ù†ÛÛŒÚº Ø¯ÛŒØªÛ’Û”",
      "Performance is displayed only when tracked data exists.": "Ú©Ø§Ø±Ú©Ø±Ø¯Ú¯ÛŒ ØµØ±Ù ØªØ¨ Ø¯Ú©Ú¾Ø§Ø¦ÛŒ Ø¬Ø§ØªÛŒ ÛÛ’ Ø¬Ø¨ Ø­Ù‚ÛŒÙ‚ÛŒ Ù¹Ø±ÛŒÚ© Ø´Ø¯Û ÚˆÛŒÙ¹Ø§ Ù…ÙˆØ¬ÙˆØ¯ ÛÙˆÛ”",
      "Common questions before subscribing.": "Ø³Ø¨Ø³Ú©Ø±Ø§Ø¦Ø¨ Ú©Ø±Ù†Û’ Ø³Û’ Ù¾ÛÙ„Û’ Ø¹Ø§Ù… Ø³ÙˆØ§Ù„Ø§ØªÛ”",
      "Does Nexora guarantee profit?": "Ú©ÛŒØ§ Nexora Ù…Ù†Ø§ÙØ¹ Ú©ÛŒ Ø¶Ù…Ø§Ù†Øª Ø¯ÛŒØªØ§ ÛÛ’ØŸ",
      "No. It provides AI-assisted market analysis and structured alerts. Trading outcomes are never guaranteed.": "Ù†ÛÛŒÚºÛ” ÛŒÛ AI Ù…Ø§Ø±Ú©ÛŒÙ¹ ØªØ¬Ø²ÛŒÛ Ø§ÙˆØ± Ù…Ù†Ø¸Ù… Ø§Ù„Ø±Ù¹Ø³ ÙØ±Ø§ÛÙ… Ú©Ø±ØªØ§ ÛÛ’Û” Ù†ØªØ§Ø¦Ø¬ Ú©Ø¨Ú¾ÛŒ Ø¶Ù…Ø§Ù†Øª Ø´Ø¯Û Ù†ÛÛŒÚº ÛÙˆØªÛ’Û”",
      "How do I receive signals?": "Ù…Ø¬Ú¾Û’ Ø³Ú¯Ù†Ù„Ø² Ú©ÛŒØ³Û’ Ù…Ù„ÛŒÚº Ú¯Û’ØŸ",
      "Create an account, link the official Telegram bot, and keep the bot connected from your dashboard.": "Ø§Ú©Ø§Ø¤Ù†Ù¹ Ø¨Ù†Ø§Ø¦ÛŒÚºØŒ Ø¢ÙÛŒØ´Ù„ Telegram bot Ù„Ù†Ú© Ú©Ø±ÛŒÚºØŒ Ø§ÙˆØ± ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ Ø³Û’ Ø§Ø³Û’ Ú©Ù†ÛŒÚ©Ù¹ Ø±Ú©Ú¾ÛŒÚºÛ”",
      "Premium crypto signal intelligence with risk-managed delivery, Telegram connection, and a clean trading dashboard.": "Ø±Ø³Ú© Ù…ÛŒÙ†Ø¬Úˆ ÚˆÛŒÙ„ÛŒÙˆØ±ÛŒØŒ Telegram Ú©Ù†Ú©Ø´Ù† Ø§ÙˆØ± ØµØ§Ù ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ Ú©Û’ Ø³Ø§ØªÚ¾ Ù¾Ø±ÛŒÙ…ÛŒÙ… Ú©Ø±Ù¾Ù¹Ùˆ Ø³Ú¯Ù†Ù„ Ø§Ù†Ù¹ÛŒÙ„ÛŒØ¬Ù†Ø³Û”",
      "Create your account directly, then link Telegram from the dashboard or official bot.": "Ø§Ù¾Ù†Ø§ Ø§Ú©Ø§Ø¤Ù†Ù¹ Ø¨Ø±Ø§Û Ø±Ø§Ø³Øª Ø¨Ù†Ø§Ø¦ÛŒÚºØŒ Ù¾Ú¾Ø± ÚˆÛŒØ´ Ø¨ÙˆØ±Úˆ ÛŒØ§ Ø¢ÙÛŒØ´Ù„ bot Ø³Û’ Telegram Ù„Ù†Ú© Ú©Ø±ÛŒÚºÛ”"
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
      btn.innerHTML='<span class="dark-icon">â—</span><span class="light-icon">â˜€</span>';
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
