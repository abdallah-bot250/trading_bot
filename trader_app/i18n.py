from flask import request, session, url_for


SUPPORTED_LANGUAGES = {"en", "ar"}
DEFAULT_LANGUAGE = "en"


TRANSLATIONS = {
    "brand": {"en": "Nexora AI Trader", "ar": "Nexora AI Trader"},
    "language.english": {"en": "English", "ar": "English"},
    "language.arabic": {"en": "العربية", "ar": "العربية"},
    "nav.home": {"en": "Home", "ar": "الرئيسية"},
    "nav.proof": {"en": "Proof", "ar": "الإثباتات"},
    "nav.bot_check": {"en": "Bot Check", "ar": "فحص البوت"},
    "nav.dashboard": {"en": "Dashboard", "ar": "لوحة التحكم"},
    "nav.login": {"en": "Login", "ar": "تسجيل الدخول"},
    "nav.register": {"en": "Get Started", "ar": "ابدأ الآن"},
    "nav.features": {"en": "Features", "ar": "المميزات"},
    "nav.pricing": {"en": "Pricing", "ar": "الأسعار"},
    "nav.demo": {"en": "Live Demo", "ar": "ديمو مباشر"},
}


def normalize_language(value):
    value = (value or "").strip().lower()
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def current_language():
    return normalize_language(session.get("lang") or request.args.get("lang"))


def direction():
    return "rtl" if current_language() == "ar" else "ltr"


def translate(key, **kwargs):
    item = TRANSLATIONS.get(key, {})
    text = item.get(current_language()) or item.get(DEFAULT_LANGUAGE) or key
    return text.format(**kwargs) if kwargs else text


def language_url(lang):
    return url_for("public.set_language", lang=normalize_language(lang), next=request.full_path)


def register_i18n(app):
    @app.context_processor
    def inject_i18n():
        lang = current_language()
        return {
            "current_lang": lang,
            "direction": "rtl" if lang == "ar" else "ltr",
            "t": translate,
            "language_url": language_url,
        }

