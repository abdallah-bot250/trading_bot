package net.nexoratrader.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String SITE_URL = "https://nexoratrader.net/";
    private static final String TELEGRAM_URL = "https://t.me/pro_crypto_99_bot";
    private static final String PACKAGE_ID = "net.nexoratrader.app";
    private static final int FILE_CHOOSER_REQUEST = 4100;

    private FrameLayout root;
    private LinearLayout appShell;
    private FrameLayout webFrame;
    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout offlineView;
    private FrameLayout splashView;
    private TextView pullHint;
    private ValueCallback<Uri[]> filePathCallback;
    private float touchStartY;
    private boolean internetLostShown = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#08111F"));
        getWindow().setNavigationBarColor(Color.parseColor("#08111F"));
        createNotificationChannels();
        buildLayout();
        configureWebView();
        showSplash();
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                hideSplash();
                if (isOnline()) {
                    webView.loadUrl(SITE_URL);
                } else {
                    showOffline(true);
                }
            }
        }, 1900);
    }

    private void buildLayout() {
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#08111F"));

        appShell = new LinearLayout(this);
        appShell.setOrientation(LinearLayout.VERTICAL);
        appShell.setBackgroundColor(Color.parseColor("#08111F"));
        root.addView(appShell, fill());

        appShell.addView(buildToolbar(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(76)));

        webFrame = new FrameLayout(this);
        webFrame.setBackgroundColor(Color.parseColor("#08111F"));
        appShell.addView(webFrame, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        webView = new WebView(this);
        webFrame.addView(webView, fill());

        pullHint = new TextView(this);
        pullHint.setText("Release to refresh");
        pullHint.setTextColor(Color.parseColor("#D4AF37"));
        pullHint.setTextSize(12);
        pullHint.setTypeface(null, Typeface.BOLD);
        pullHint.setGravity(Gravity.CENTER);
        pullHint.setPadding(dp(12), dp(6), dp(12), dp(6));
        pullHint.setBackground(rounded(Color.parseColor("#D4AF37"), Color.parseColor("#1A2638"), 14));
        pullHint.setVisibility(View.GONE);
        FrameLayout.LayoutParams hintParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hintParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        hintParams.topMargin = dp(12);
        webFrame.addView(pullHint, hintParams);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3));
        progressParams.gravity = Gravity.TOP;
        webFrame.addView(progressBar, progressParams);

        offlineView = buildOfflineView();
        offlineView.setVisibility(View.GONE);
        webFrame.addView(offlineView, fill());

        appShell.addView(buildBottomNav(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(78)));

        splashView = buildSplashView();
        root.addView(splashView, fill());
        setContentView(root);
    }

    private View buildToolbar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(16), dp(10), dp(14), dp(10));
        bar.setBackgroundColor(Color.parseColor("#08111F"));

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("nexora_splash_logo", "drawable", getPackageName()));
        bar.addView(logo, new LinearLayout.LayoutParams(dp(46), dp(46)));

        LinearLayout titleBox = new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setPadding(dp(10), 0, 0, 0);
        TextView title = new TextView(this);
        title.setText("NEXORA");
        title.setTextColor(Color.WHITE);
        title.setTextSize(17);
        title.setTypeface(null, Typeface.BOLD);
        title.setLetterSpacing(.08f);
        TextView sub = new TextView(this);
        sub.setText("AI TRADER");
        sub.setTextColor(Color.parseColor("#D4AF37"));
        sub.setTextSize(10);
        sub.setTypeface(null, Typeface.BOLD);
        sub.setLetterSpacing(.22f);
        titleBox.addView(title);
        titleBox.addView(sub);
        bar.addView(titleBox, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        bar.addView(toolbarButton("Share", "S", new View.OnClickListener() { public void onClick(View v) { shareApp(); } }));
        bar.addView(toolbarButton("Telegram", "T", new View.OnClickListener() { public void onClick(View v) { openExternal(TELEGRAM_URL); } }));
        bar.addView(toolbarButton("Menu", "M", new View.OnClickListener() { public void onClick(View v) { showNativeMenu(); } }));
        return bar;
    }

    private View toolbarButton(String label, String icon, View.OnClickListener listener) {
        TextView b = new TextView(this);
        b.setText(icon);
        b.setContentDescription(label);
        b.setTextColor(Color.parseColor("#D4AF37"));
        b.setTextSize(16);
        b.setGravity(Gravity.CENTER);
        b.setTypeface(null, Typeface.BOLD);
        b.setBackground(rounded(Color.parseColor("#263244"), Color.parseColor("#101826"), 16));
        b.setOnClickListener(listener);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(42), dp(42));
        p.leftMargin = dp(8);
        b.setLayoutParams(p);
        return b;
    }

    private View buildBottomNav() {
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(7), dp(8), dp(7));
        nav.setBackgroundColor(Color.parseColor("#08111F"));
        addNavItem(nav, "H", "Home", SITE_URL + "dashboard");
        addNavItem(nav, "S", "Signals", SITE_URL + "signals");
        addNavItem(nav, "A", "Auto", SITE_URL + "auto-trade");
        addNavItem(nav, "E", "Earn", SITE_URL + "pricing");
        addNavItem(nav, "P", "Account", SITE_URL + "profile");
        return nav;
    }

    private void addNavItem(LinearLayout nav, String icon, String label, final String url) {
        LinearLayout item = new LinearLayout(this);
        item.setOrientation(LinearLayout.VERTICAL);
        item.setGravity(Gravity.CENTER);
        item.setPadding(dp(4), dp(4), dp(4), dp(4));
        TextView i = new TextView(this);
        i.setText(icon);
        i.setTextColor(Color.parseColor("#D4AF37"));
        i.setTextSize(17);
        i.setTypeface(null, Typeface.BOLD);
        i.setGravity(Gravity.CENTER);
        TextView l = new TextView(this);
        l.setText(label);
        l.setTextColor(Color.parseColor("#D7DEE9"));
        l.setTextSize(10);
        l.setGravity(Gravity.CENTER);
        item.addView(i);
        item.addView(l);
        item.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { loadInternal(url); } });
        nav.addView(item, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1));
    }

    private LinearLayout buildOfflineView() {
        LinearLayout offline = new LinearLayout(this);
        offline.setOrientation(LinearLayout.VERTICAL);
        offline.setGravity(Gravity.CENTER);
        offline.setPadding(dp(28), dp(28), dp(28), dp(28));
        offline.setBackgroundColor(Color.parseColor("#08111F"));

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("nexora_splash_logo", "drawable", getPackageName()));
        offline.addView(logo, new LinearLayout.LayoutParams(dp(100), dp(100)));

        TextView title = new TextView(this);
        title.setText("Connection Lost");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setTypeface(null, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);
        title.setPadding(0, dp(16), 0, 0);

        TextView message = new TextView(this);
        message.setText("Nexora needs internet access to open your trading console.");
        message.setTextColor(Color.parseColor("#B9C3D4"));
        message.setTextSize(15);
        message.setGravity(Gravity.CENTER);
        message.setPadding(0, dp(12), 0, dp(20));

        TextView retry = premiumButton("Try Again");
        retry.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (isOnline()) {
                    offlineView.setVisibility(View.GONE);
                    webView.setVisibility(View.VISIBLE);
                    webView.loadUrl(SITE_URL);
                } else {
                    showInternetLostDialog();
                }
            }
        });

        offline.addView(title);
        offline.addView(message);
        offline.addView(retry, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return offline;
    }

    private FrameLayout buildSplashView() {
        FrameLayout splash = new FrameLayout(this);
        splash.setBackgroundColor(Color.parseColor("#08111F"));
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER);
        card.setPadding(dp(30), dp(30), dp(30), dp(30));

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("nexora_splash_logo", "drawable", getPackageName()));
        card.addView(logo, new LinearLayout.LayoutParams(dp(142), dp(142)));

        TextView title = new TextView(this);
        title.setText("NEXORA AI TRADER");
        title.setTextColor(Color.WHITE);
        title.setTextSize(26);
        title.setTypeface(null, Typeface.BOLD);
        title.setLetterSpacing(.1f);
        title.setGravity(Gravity.CENTER);
        title.setPadding(0, dp(18), 0, 0);
        card.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("AI Powered Crypto Trading");
        subtitle.setTextColor(Color.parseColor("#D4AF37"));
        subtitle.setTextSize(15);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, dp(8), 0, dp(22));
        card.addView(subtitle);

        ProgressBar loader = new ProgressBar(this);
        card.addView(loader, new LinearLayout.LayoutParams(dp(44), dp(44)));

        splash.addView(card, fill());
        AlphaAnimation fade = new AlphaAnimation(.1f, 1f);
        fade.setDuration(850);
        fade.setRepeatCount(Animation.INFINITE);
        fade.setRepeatMode(Animation.REVERSE);
        logo.startAnimation(fade);
        return splash;
    }

    private void showSplash() {
        splashView.setVisibility(View.VISIBLE);
        appShell.setAlpha(0f);
    }

    private void hideSplash() {
        AlphaAnimation out = new AlphaAnimation(1f, 0f);
        out.setDuration(320);
        out.setAnimationListener(new Animation.AnimationListener() {
            public void onAnimationStart(Animation animation) {}
            public void onAnimationRepeat(Animation animation) {}
            public void onAnimationEnd(Animation animation) { splashView.setVisibility(View.GONE); }
        });
        splashView.startAnimation(out);
        appShell.animate().alpha(1f).setDuration(360).start();
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setSupportMultipleWindows(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setUserAgentString(settings.getUserAgentString() + " NexoraAndroidApp/2.0");

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        webView.setBackgroundColor(Color.parseColor("#08111F"));
        webView.setWebViewClient(new NexoraWebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (MainActivity.this.filePathCallback != null) {
                    MainActivity.this.filePathCallback.onReceiveValue(null);
                }
                MainActivity.this.filePathCallback = filePathCallback;
                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                } catch (Exception e) {
                    MainActivity.this.filePathCallback = null;
                    showMessage("No file picker found on this device.");
                    return false;
                }
                return true;
            }
        });

        webView.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                if (event.getAction() == MotionEvent.ACTION_DOWN) {
                    touchStartY = event.getY();
                } else if (event.getAction() == MotionEvent.ACTION_MOVE && webView.getScrollY() == 0 && event.getY() - touchStartY > dp(95)) {
                    pullHint.setVisibility(View.VISIBLE);
                } else if (event.getAction() == MotionEvent.ACTION_UP) {
                    if (pullHint.getVisibility() == View.VISIBLE) {
                        pullHint.setVisibility(View.GONE);
                        webView.reload();
                    }
                }
                return false;
            }
        });
    }

    private class NexoraWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            return handleUrl(request.getUrl().toString());
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            return handleUrl(url);
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (request != null && request.isForMainFrame()) {
                showOffline(false);
            }
        }
    }

    private boolean handleUrl(String url) {
        if (url == null) return false;
        Uri uri = Uri.parse(url);
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
        String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase();

        if (scheme.equals("tel") || scheme.equals("mailto") || scheme.equals("tg") || scheme.equals("whatsapp")) {
            openExternal(url);
            return true;
        }
        if (host.equals("nexoratrader.net") || host.equals("www.nexoratrader.net")) {
            return false;
        }
        if (host.contains("t.me") || host.contains("telegram.me") || host.contains("wa.me") || host.contains("whatsapp.com")) {
            openExternal(url);
            return true;
        }
        if (host.contains("nowpayments") || host.contains("stripe") || host.contains("paypal") || host.contains("checkout") || host.contains("payment")) {
            openExternal(url);
            return true;
        }
        if (scheme.startsWith("http")) {
            openExternal(url);
            return true;
        }
        return false;
    }

    private void loadInternal(String url) {
        if (!isOnline()) {
            showOffline(true);
            return;
        }
        offlineView.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        webView.loadUrl(url);
    }

    private void openExternal(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            startActivity(intent);
        } catch (Exception e) {
            showMessage("Unable to open this link.");
        }
    }

    private void showNativeMenu() {
        final String[] items = new String[]{"Open Telegram", "Open Website", "Contact Support", "Share App", "Rate App", "Check for Updates", "About Nexora"};
        new AlertDialog.Builder(this)
                .setTitle("Nexora AI Trader")
                .setItems(items, new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        if (which == 0) openExternal(TELEGRAM_URL);
                        if (which == 1) openExternal(SITE_URL);
                        if (which == 2) openExternal(TELEGRAM_URL);
                        if (which == 3) shareApp();
                        if (which == 4) rateApp();
                        if (which == 5) showUpdateDialog();
                        if (which == 6) showAboutDialog();
                    }
                })
                .show();
    }

    private void shareApp() {
        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("text/plain");
        share.putExtra(Intent.EXTRA_SUBJECT, "Nexora AI Trader");
        share.putExtra(Intent.EXTRA_TEXT, "Nexora AI Trader - AI-assisted crypto signals delivered to Telegram. " + SITE_URL);
        startActivity(Intent.createChooser(share, "Share Nexora"));
    }

    private void rateApp() {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + PACKAGE_ID)));
        } catch (Exception e) {
            openExternal("https://play.google.com/store/apps/details?id=" + PACKAGE_ID);
        }
    }

    private void showUpdateDialog() {
        new AlertDialog.Builder(this)
                .setTitle("You are up to date")
                .setMessage("Nexora AI Trader will notify you here when a new app version is available.")
                .setPositiveButton("OK", null)
                .show();
    }

    private void showAboutDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Nexora AI Trader")
                .setMessage("Version 1.0.0\nAI-assisted crypto signal dashboard with Telegram delivery.\n\nCrypto trading is risky. Not financial advice.")
                .setPositiveButton("OK", null)
                .show();
    }

    private void showInternetLostDialog() {
        if (internetLostShown) return;
        internetLostShown = true;
        new AlertDialog.Builder(this)
                .setTitle("Internet connection lost")
                .setMessage("Please reconnect to continue using Nexora AI Trader.")
                .setPositiveButton("OK", new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface d, int w) { internetLostShown = false; }
                })
                .show();
    }

    private boolean isOnline() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            NetworkInfo info = cm != null ? cm.getActiveNetworkInfo() : null;
            return info != null && info.isConnected();
        } catch (Exception e) {
            return true;
        }
    }

    private void showOffline(boolean withDialog) {
        webView.setVisibility(View.GONE);
        offlineView.setVisibility(View.VISIBLE);
        progressBar.setVisibility(View.GONE);
        if (withDialog) showInternetLostDialog();
    }

    private void showMessage(String message) {
        new AlertDialog.Builder(this)
                .setTitle("Nexora AI Trader")
                .setMessage(message)
                .setPositiveButton("OK", null)
                .show();
    }

    private TextView premiumButton(String text) {
        TextView b = new TextView(this);
        b.setText(text);
        b.setTextColor(Color.parseColor("#08111F"));
        b.setTextSize(16);
        b.setGravity(Gravity.CENTER);
        b.setTypeface(null, Typeface.BOLD);
        b.setPadding(dp(28), dp(13), dp(28), dp(13));
        b.setBackground(rounded(Color.parseColor("#D4AF37"), Color.parseColor("#D4AF37"), 18));
        return b;
    }

    private GradientDrawable rounded(int strokeColor, int fillColor, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fillColor);
        d.setCornerRadius(dp(radius));
        d.setStroke(dp(1), strokeColor);
        return d;
    }

    private FrameLayout.LayoutParams fill() {
        return new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        manager.createNotificationChannel(new NotificationChannel("signals", "Signal Alerts", NotificationManager.IMPORTANCE_HIGH));
        manager.createNotificationChannel(new NotificationChannel("announcements", "Announcements", NotificationManager.IMPORTANCE_DEFAULT));
        manager.createNotificationChannel(new NotificationChannel("marketing", "Marketing Notifications", NotificationManager.IMPORTANCE_LOW));
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST && filePathCallback != null) {
            Uri[] results = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
