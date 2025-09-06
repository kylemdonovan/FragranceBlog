from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
login = LoginManager()
login.login_view = 'main.login'
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info'
