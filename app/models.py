# app/models.py
from datetime import datetime, timezone # Use timezone-aware datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login # Import db and login from app package __init__
from slugify import slugify as default_slugify
# Flask-Login user loader callback
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id)) # Use session.get for primary key lookup

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False) # Added email
    password_hash = db.Column(db.String(256)) # Increased length for potentially longer hashes
    is_admin = db.Column(db.Boolean, default=False) # Flag for admin status

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='commenter', lazy='dynamic') # Changed backref

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    # --- ADD THIS LINE ---
    slug = db.Column(db.String(150), unique=True, index=True, nullable=False) # Length slightly > title
    # -------------------
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    # --- ADD THIS HELPER METHOD ---
    # Automatically generate slug before saving (can be called explicitly)
    @staticmethod
    def generate_unique_slug(title):
        base_slug = default_slugify(title)
        slug = base_slug
        counter = 1
        # Check if slug already exists in the DB
        while Post.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug
    # ----------------------------

    def __repr__(self):
        return f'<Post {self.title}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Assuming comments require login
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'
        
