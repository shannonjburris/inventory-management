from flask import jsonify


def register_error_handlers(app):
    """
    Register JSON error handlers for common HTTP error codes.
    Every error response uses the same envelope shape so API clients
    always know where to find the message and details.

    In Express you'd do: app.use((err, req, res, next) => res.status(err.status).json(...))
    In Flask, each status code gets its own decorated handler function.
    """

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": {
                "code": 400,
                "message": "Bad request",
                # error.description carries the detail we set when calling abort(400, description=...)
                "details": error.description,
            }
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": {
                "code": 404,
                "message": str(error.description) if error.description else "Not found",
                "details": None,
            }
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": {
                "code": 405,
                "message": "Method not allowed",
                "details": None,
            }
        }), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "error": {
                "code": 500,
                "message": "Internal server error",
                "details": None,
            }
        }), 500
