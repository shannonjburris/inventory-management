import logging
from flask import jsonify

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Register JSON error handlers for common HTTP error codes.

    Why do this at all? Flask's default error responses are HTML pages.
    An API client expecting JSON would have no idea how to parse that.
    These handlers intercept every error and return a consistent JSON envelope
    so clients always know exactly where to find the error information.
    """

    @app.errorhandler(400)
    def bad_request(error):
        # 400 = the client sent something invalid (missing field, wrong type, etc.)
        # details carries the Pydantic validation error list when validation fails,
        # or a plain string message for other bad requests (e.g. invalid JSON body)
        return jsonify({
            "error": {
                "code": 400,
                "message": "Bad request",
                "details": error.description,  # set by abort(400, description=...)
            }
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        # 404 = the requested resource doesn't exist
        # details is None because there's nothing more to say beyond the message
        return jsonify({
            "error": {
                "code": 404,
                "message": str(error.description) if error.description else "Not found",
                "details": None,
            }
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        # 405 = the URL exists but not for this HTTP method
        # e.g. sending a DELETE to /products/analytics
        return jsonify({
            "error": {
                "code": 405,
                "message": "Method not allowed",
                "details": None,
            }
        }), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the full error server-side so it's visible in `docker-compose logs api`
        # but return a vague message to the client — never expose internal stack traces
        logger.error("Internal server error: %s", error)
        return jsonify({
            "error": {
                "code": 500,
                "message": "Internal server error",
                "details": None,
            }
        }), 500
