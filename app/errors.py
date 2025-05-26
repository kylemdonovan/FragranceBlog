from flask import render_template, Blueprint, current_app, request
from app import db  # Import db if you need to rollback sessions on 500 errors

# Create a Blueprint for error handlers
# This name 'errors' is just for organization within this file;
# the handlers are registered app-wide via app_errorhandler.
bp = Blueprint('errors', __name__)


@bp.app_errorhandler(404)  # Registers this function to handle all 404 errors for the app
def not_found_error(error):
    # Log the 404 error with the path that was not found
    current_app.logger.warning(
        f"404 Not Found: The requested URL {request.path} was not found on the server. Error details: {error}")
    return render_template('errors/404.html'), 404  # Render the 404.html template


@bp.app_errorhandler(500)  # Registers this function to handle all 500 errors for the app
def internal_error(error):
    # It's good practice to rollback the database session in case the error
    # was caused by a failed database operation that left the session in an inconsistent state.
    try:
        db.session.rollback()
        current_app.logger.info("Session rolled back successfully due to 500 error.")
    except Exception as e:
        # Log if rollback itself fails, but don't let it prevent showing the 500 page
        current_app.logger.error(f"Error during session rollback in 500 handler: {e}", exc_info=True)

    # Log the 500 error with details and traceback
    current_app.logger.error(
        f"500 Internal Server Error: An unexpected error occurred. URL: {request.url} Error details: {error}",
        exc_info=True)
    return render_template('errors/500.html'), 500  # Render the 500.html template


@bp.app_errorhandler(403)
def forbidden_error(error):
    current_app.logger.warning(f"403 Forbidden: Access denied to {request.path}. Error details: {error}")
    return render_template('errors/403.html'), 403
