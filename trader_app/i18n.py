from flask import request, session, url_for


SUPPORTED_LANGUAGE_META = {
    "en": {"name": "English", "native": "English", "dir": "ltr", "flag": "US"},
    "ar": {"name": "Arabic", "native": "العربية", "dir": "rtl", "flag": "AE"},
    "es": {"name": "Spanish", "native": "Español", "dir": "ltr", "flag": "ES"},
    "fr": {"name": "French", "native": "Français", "dir": "ltr", "flag": "FR"},
    "de": {"name": "German", "native": "Deutsch", "dir": "ltr", "flag": "DE"},
    "tr": {"name": "Turkish", "native": "Türkçe", "dir": "ltr", "flag": "TR"},
    "pt": {"name": "Portuguese", "native": "Português", "dir": "ltr", "flag": "PT"},
    "ru": {"name": "Russian", "native": "Русский", "dir": "ltr", "flag": "RU"},
    "zh": {"name": "Chinese", "native": "中文", "dir": "ltr", "flag": "CN"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "dir": "ltr", "flag": "IN"},
    "ur": {"name": "Urdu", "native": "اردو", "dir": "rtl", "flag": "PK"},
    "id": {"name": "Indonesian", "native": "Bahasa Indonesia", "dir": "ltr", "flag": "ID"},
}
SUPPORTED_LANGUAGES = set(SUPPORTED_LANGUAGE_META)
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
    "nav.demo": {"en": "Live Demo", "ar": "عرض مباشر"},
}


def normalize_language(value):
    value = (value or "").strip().lower()
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def current_language():
    return normalize_language(session.get("lang") or request.args.get("lang"))


def direction():
    return SUPPORTED_LANGUAGE_META.get(current_language(), {}).get("dir", "ltr")


def translate(key, **kwargs):
    item = TRANSLATIONS.get(key, {})
    text = item.get(current_language()) or item.get(DEFAULT_LANGUAGE) or key
    return text.format(**kwargs) if kwargs else text


def language_url(lang):
    return url_for("public.set_language", lang=normalize_language(lang), next=request.full_path)


def supported_languages():
    return [{"code": code, **meta} for code, meta in SUPPORTED_LANGUAGE_META.items()]


def register_i18n(app):
    @app.context_processor
    def inject_i18n():
        lang = current_language()
        return {
            "current_lang": lang,
            "direction": SUPPORTED_LANGUAGE_META.get(lang, {}).get("dir", "ltr"),
            "supported_languages": supported_languages(),
            "t": translate,
            "language_url": language_url,
        }
