from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .extensions import limiter
from .i18n import register_i18n
from .logging_config import configure_logging
from .services.performance import apply_performance_headers, init_compression
from .services.runtime import enforce_session_timeout, inject_csrf_helpers, init_db, protect_post_requests, redirect_legacy_domains
from .blueprints import (
    admin_bp,
    auth_bp,
    dashboard_bp,
    health_bp,
    payments_bp,
    public_bp,
    telegram_bp,
)


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)
    app.secret_key = app.config["SECRET_KEY"]

    configure_logging(app)
    limiter.init_app(app)
    init_compression(app)

    try:
        from flask_talisman import Talisman

        Talisman(
            app,
            force_https=app.config.get("STRICT_HTTPS", True),
            content_security_policy=None,
            frame_options="DENY",
            referrer_policy="strict-origin-when-cross-origin",
        )
    except Exception as exc:
        app.logger.warning("Flask-Talisman is not installed or failed to initialize: %s", exc)

    app.context_processor(inject_csrf_helpers)
    register_i18n(app)
    app.before_request(redirect_legacy_domains)
    app.before_request(enforce_session_timeout)
    app.before_request(protect_post_requests)
    app.after_request(apply_performance_headers)

    app.register_blueprint(public_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(telegram_bp)

    register_error_handlers(app)
    init_db()

    return app
