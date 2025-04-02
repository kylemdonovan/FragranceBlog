# run.py
from app import create_app, db # Import db as well
from app.models import User, Post, Comment # Import models

app = create_app()

# Optional: Create database tables if they don't exist
# This is useful for the very first run without migrations set up
# You might remove this once migrations are reliably used.
# with app.app_context():
#    db.create_all()

if __name__ == '__main__':
    # Set debug=True for development (auto-reloads, debugger)
    # NEVER run with debug=True in production!
    app.run(debug=True)

