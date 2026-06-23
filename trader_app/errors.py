from flask import jsonify, request
from werkzeug.exceptions import HTTPException


def wants_json_response():
    return request.path.startswith("/api/") or request.path.endswith("webhook")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        if wants_json_response():
            return jsonify({"status": "error", "error": "not_found"}), 404
        return "Not Found", 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled server error: %s", error)
        if wants_json_response():
            return jsonify({"status": "error", "error": "internal_server_error"}), 500
        return "Internal Server Error", 500

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled exception: %s", error)
        if wants_json_response():
            return jsonify({"status": "error", "error": "internal_server_error"}), 500
        return "Internal Server Error", 500
