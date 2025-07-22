# run.py (in your project root)
import os # For PORT environment variable
from app import create_app, db # Assuming db is initialized in create_app or globally in app/__init__
from app.models import User, Post, Comment, Tag # Import all your models
from flask_migrate import Migrate # For flask db commands via shell

app = create_app() # This should use your Config class which reads .env
migrate = Migrate(app, db) # Initialize Flask-Migrate here

# This runs `flask shell` and have db, models, app available
# This will effectively use the shell context defined in app/__init__.py


# === TEMPORARY SECRET ROUTE FOR ADMIN SETUP ===
# !!! IMPORTANT: REMOVE THIS ROUTE AFTER USE !!!
@bp.route('/i-am-a-silly-goose-who-forgot-his-password')
def secret_admin_setup():
    # Prevent this from being run by anyone else if possible
    # A simple check could be to look for a specific query param
    # For now, the secret URL is our main protection.

    try:
        # --- OPTION A: Reset password for existing admin ---
        # Use this if you think you created 'youradmin' but forgot the password
        admin_user = db.session.scalar(
            db.select(User).where(User.username == 'youradmin'))
        if admin_user:
            new_password = 'A_New_Very_Strong_Password_123!'  # CHANGE THIS
            admin_user.set_password(new_password)
            db.session.commit()
            message = f"Password for existing user 'youradmin' has been reset to '{new_password}'."
            current_app.logger.info(message)
            flash(message, 'success')
            return redirect(url_for('main.index'))

        # --- OPTION B: Create a new admin if one doesn't exist ---
        # Use this if the user creation might have failed or you want a new one.
        else:
            new_password = 'A_New_Very_Strong_Password_123!'  # CHANGE THIS
            admin_user = User(
                username='youradmin',
                email='youradmin@example.com',  # Change this if needed
                is_admin=True
            )
            admin_user.set_password(new_password)
            db.session.add(admin_user)
            db.session.commit()
            message = f"NEW admin user 'youradmin' has been created with password '{new_password}'."
            current_app.logger.info(message)
            flash(message, 'success')
            return redirect(url_for('main.index'))

    except Exception as e:
        db.session.rollback()
        message = f"An error occurred during secret admin setup: {e}"
        current_app.logger.error(message, exc_info=True)
        flash(message, 'danger')
        return redirect(url_for('main.index'))




# This run.py is mainly for Gunicorn and the `if __name__ == '__main__':` block.

if __name__ == '__main__':
    # This block is for running the Flask development server directly
    # (e.g., python run.py). Gunicorn will not use this.
    # Render uses the PORT environment variable it assigns.
    port = int(os.environ.get('PORT', 5000))
    # Set debug based on an environment variable, default to True for local
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
