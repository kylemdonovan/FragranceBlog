# app/routes.py
from flask import render_template, flash, redirect, url_for, request, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa # Import sqlalchemy
from app import db       # Import db from the app package
from app.models import User, Post, Comment
from app.forms import LoginForm, RegistrationForm, PostForm, CommentForm
from urllib.parse import urlsplit # For redirect safety
from functools import wraps


# Create a Blueprint instance
bp = Blueprint('main', __name__)

# --- Public Routes ---

@bp.route('/')
@bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    # Order posts by newest first
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=5, error_out=False) # Use pagination

    next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html', title='Home', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)

@bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post_obj = db.get_or_404(Post, post_id) # Use get_or_404 for cleaner handling
    form = CommentForm()
    if form.validate_on_submit() and current_user.is_authenticated: # Check login for comments
        comment = Comment(body=form.body.data, commenter=current_user, post=post_obj)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.', 'success')
        return redirect(url_for('main.post', post_id=post_id)) # Redirect to clear form
    elif form.validate_on_submit() and not current_user.is_authenticated:
         flash('You must be logged in to comment.', 'warning')
         return redirect(url_for('main.login', next=url_for('main.post', post_id=post_id)))

    # Fetch comments for the post, newest first
    page = request.args.get('page', 1, type=int)
    comments_query = post_obj.comments.select().order_by(Comment.timestamp.desc())
    comments = db.paginate(comments_query, page=page, per_page=10, error_out=False)

    next_url = url_for('main.post', post_id=post_id, page=comments.next_num) if comments.has_next else None
    prev_url = url_for('main.post', post_id=post_id, page=comments.prev_num) if comments.has_prev else None

    return render_template('post.html', title=post_obj.title, post=post_obj, form=form,
                           comments=comments.items, next_url=next_url, prev_url=prev_url)

# --- Authentication Routes ---

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Already logged in
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        # Security: Check if the next URL is safe
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '': # If no next or it's an external URL
            next_page = url_for('main.index') # Default redirect
        flash('Login successful!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# --- User Management Route (Protected) ---

def admin_required(f):
    @wraps(f)
    @login_required # Ensure user is logged in first
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin/register', methods=['GET', 'POST']) # CHANGED URL
@admin_required                                       # ADDED Decorator
def register():


    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)

        # REMOVE the User.query.count() check - it's no longer needed
        # and could potentially cause issues if reused later.
        # Set all users created via this form to non-admins.
        user.is_admin = False
        flash(f'User {user.username} created successfully!', 'success') # Adjusted message

        db.session.add(user)
        db.session.commit()
        # Redirect to admin dashboard after creating a user
        return redirect(url_for('main.admin_dashboard')) # CHANGED Redirect

    # Render the same template, just change the title passed
    return render_template('register.html', title='Register New User', form=form) # CHANGED Title

# --- Admin Routes (Protected) ---




@bp.route('/admin')
@admin_required
def admin_dashboard():
    # Simple dashboard showing posts to manage
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=10, error_out=False)

    next_url = url_for('main.admin_dashboard', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.admin_dashboard', page=posts.prev_num) if posts.has_prev else None

    return render_template('admin/dashboard.html', title='Admin Dashboard', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/admin/post/new', methods=['GET', 'POST'])
@admin_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.body.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('main.admin_dashboard')) # Redirect to admin dashboard
    return render_template('admin/create_edit_post.html', title='Create New Post', form=form, legend='New Post')

@bp.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    post = db.get_or_404(Post, post_id)
    # Optional: Add check if current_user == post.author if needed, but admin should override
    form = PostForm()
    if form.validate_on_submit(): # Data submitted via POST
        post.title = form.title.data
        post.body = form.body.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('main.post', post_id=post.id))
    elif request.method == 'GET': # Populate form with existing data
        form.title.data = post.title
        form.body.data = post.body
    return render_template('admin/create_edit_post.html', title='Edit Post', form=form, legend='Edit Post')

@bp.route('/admin/post/<int:post_id>/delete', methods=['POST']) # Use POST for deletion
@admin_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    # Optional: Add author check if needed
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.admin_dashboard')) # Redirect to admin dashboard
    
