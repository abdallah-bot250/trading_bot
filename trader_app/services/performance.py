from flask import current_app, request


STATIC_EXTENSIONS = (
    ".css",
    ".js",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".webmanifest",
)


def init_compression(app):
    try:
        from flask_compress import Compress

        Compress(app)
        app.logger.info("Flask-Compress initialized")
    except Exception as exc:
        app.logger.warning("Flask-Compress is not installed or failed to initialize: %s", exc)


def apply_performance_headers(response):
    path = request.path.lower()

    if path.startswith("/static/") or path.endswith(STATIC_EXTENSIONS):
        max_age = int(current_app.config.get("CACHE_STATIC_SECONDS", 60 * 60 * 24 * 30))
        response.headers["Cache-Control"] = f"public, max-age={max_age}, immutable"
    elif request.method == "GET" and response.status_code == 200 and not request.path.startswith(("/dashboard", "/admin", "/invoice-history")):
        max_age = int(current_app.config.get("CACHE_PUBLIC_SECONDS", 300))
        response.headers.setdefault("Cache-Control", f"public, max-age={max_age}")
    else:
        response.headers.setdefault("Cache-Control", "no-store")

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Vary", "Accept-Encoding")
    return response
