# run.py (in your project root)
import os # For PORT environment variable
from app import create_app, db # Assuming db is initialized in create_app or globally in app/__init__
from app.models import User, Post, Comment, Tag # Import all your models
from flask_migrate import Migrate # For flask db commands via shell

app = create_app() # This should use your Config class which reads .env
migrate = Migrate(app, db) # Initialize Flask-Migrate here

# This runs `flask shell` and have db, models, app available
# This will effectively use the shell context defined in app/__init__.py









# This run.py is mainly for Gunicorn and the `if __name__ == '__main__':` block.

if __name__ == '__main__':
    # This block is for running the Flask development server directly
    # (e.g., python run.py). Gunicorn will not use this.
    # Render uses the PORT environment variable it assigns.
    port = int(os.environ.get('PORT', 5000))
    # Set debug based on an environment variable, default to True for local
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
