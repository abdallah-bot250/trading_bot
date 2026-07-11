# Nexora AI Trader Android App

This is a lightweight Android WebView wrapper for the production Nexora AI Trader SaaS.

Production URL:
https://nexoratrader.net

What it includes:
- Native splash/loading experience
- Secure WebView settings
- Telegram/WhatsApp/external links opened outside the app
- Back button handling
- Network error screen
- File chooser support for website upload inputs

Build steps:
1. Open this `mobile/android` folder in Android Studio.
2. Let Android Studio sync Gradle.
3. Build a debug APK for testing.
4. Configure a release signing key.
5. Build a release AAB for Google Play.

Before Google Play submission:
- Replace placeholder app icon with final Nexora app icon.
- Add Privacy Policy URL.
- Add Terms of Service URL.
- Use risk disclaimer in the store listing.
- Do not claim guaranteed profit or guaranteed trading results.
