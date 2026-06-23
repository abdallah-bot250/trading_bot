import logging
import os


def configure_logging(app=None):
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger("ai_crypto_trader")
    logger.setLevel(level)
    if app is not None:
        app.logger.setLevel(level)
    return logger
