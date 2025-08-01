# app/models.py
from datetime import datetime, timezone  # Use timezone-aware datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login  # Import db and login from app package __init__
from slugify import slugify as default_slugify
import sqlalchemy as sa
from itsdangerous import URLSafeTimedSerializer as Serializer  # Corrected class name from previous (if any)
from flask import current_app

# -- Association Table ---
# This table connects posts and tags in many-to-many relations
post_tags = db.Table('post_tags',
                     db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
                     )


# -------------------------

# Flask-Login user loader callback
@login.user_loader
def load_user(id):
    # Use db.session.get for primary key lookup, which is efficient, probably
    return db.session.get(User, int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))  # Good length for modern hashes
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='commenter', lazy='dynamic')  # 'commenter' is a good backref name

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:  # Handle cases where password_hash might not be set
            return False
        return check_password_hash(self.password_hash, password)

    # --- <<< PASSWORD RESET TOKEN METHODS >>> ---
    def get_reset_password_token(self, expires_sec=None):  # Allow expires_sec to be configured
        """Generates a secure token for password reset."""
        if expires_sec is None:
            expires_sec = current_app.config.get('PASSWORD_RESET_EXPIRES_SEC', 1800)  # Default 30 mins
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_sec=None):
        """Verifies the reset token and returns the User if valid."""
        if expires_sec is None:
            expires_sec = current_app.config.get('PASSWORD_RESET_EXPIRES_SEC', 1800)
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
        except Exception as e:
            current_app.logger.warning(
                f"Password reset token verification failed for token '{token[:20]}...': {e}")  # Log token snippet for easier trace
            return None
        return db.session.get(User, user_id)

    # --- <<< END PASSWORD RESET TOKEN METHODS >>> ---

    def __repr__(self):
        return f'<User {self.username}>'


# -- Tag Model ---
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)

    # Relationship back to posts (already defined in Post model's backref)
    # posts = db.relationship('Post', secondary=post_tags, back_populates='tags', lazy='dynamic') # If using back_populates

    def __repr__(self):
        return f'<Tag {self.name}>'


# -----------------

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    image_public_id = db.Column(db.String(255), nullable=True)  # <-- NEW FIELD ADDED HERE
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # FIELDS FOR DRAFT/PUBLISH
    status = db.Column(db.Boolean, default=True, nullable=False, index=True)
    published_at = db.Column(db.DateTime, index=True, nullable = True)

    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=post_tags, lazy='select',
                           backref=db.backref('posts', lazy='dynamic'))  # 'select' is often good for tags

    @staticmethod
    def generate_unique_slug(title_to_slugify):  # Renamed parameter for clarity
        """Generates a unique slug from a title, appending a counter if needed."""
        base_slug = default_slugify(title_to_slugify)
        if not base_slug:  # Handle empty titles or titles that slugify to empty strings
            base_slug = "post"  # Default slug base

        slug_candidate = base_slug
        counter = 1

        while db.session.scalar(
                sa.select(Post.id).filter_by(slug=slug_candidate).limit(1)):  # Added .limit(1) for efficiency
            slug_candidate = f"{base_slug}-{counter}"
            counter += 1
        return slug_candidate

    def __repr__(self):
        return f'<Post {self.title}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by User {self.user_id} on Post {self.post_id}>'  # More descriptive repr
