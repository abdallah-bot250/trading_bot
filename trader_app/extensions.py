try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:
    Limiter = None

    def get_remote_address():
        return "unknown"


class NoopLimiter:
    def init_app(self, app):
        app.logger.warning("Flask-Limiter is not installed; rate limits are disabled.")

    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


limiter = (
    Limiter(key_func=get_remote_address)
    if Limiter is not None
    else NoopLimiter()
)
