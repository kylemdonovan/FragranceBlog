# app/routes.py
from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app
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

@bp.route('/post/<string:slug>', methods=['GET', 'POST']) # Changed from <int:post_id>
def post(slug): # Changed argument name
    # Query by slug instead of id
    post_obj = db.session.scalar(sa.select(Post).filter_by(slug=slug))
    if post_obj is None:
        flash(f'Post "{slug}" not found.', 'warning')
        return redirect(url_for('main.index')) # Or render a 404 template

    form = CommentForm()
    if form.validate_on_submit() and current_user.is_authenticated:
        comment = Comment(body=form.body.data, commenter=current_user, post=post_obj)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.', 'success')
        return redirect(url_for('main.post', slug=post_obj.slug)) # Redirect using slug
    elif form.validate_on_submit() and not current_user.is_authenticated:
         flash('You must be logged in to comment.', 'warning')
         # Redirect to login, passing the current post's slug URL as 'next'
         return redirect(url_for('main.login', next=url_for('main.post', slug=post_obj.slug)))

    # Fetch comments for the post
    page = request.args.get('page', 1, type=int)
    # Use post_obj relationship directly
    comments_query = sa.select(Comment).where(Comment.post_id == post_obj.id).order_by(Comment.timestamp.desc())
    comments = db.paginate(comments_query, page=page, per_page=10, error_out=False)

    # Pass slug to url_for for pagination links
    next_url = url_for('main.post', slug=slug, page=comments.next_num) if comments.has_next else None
    prev_url = url_for('main.post', slug=slug, page=comments.prev_num) if comments.has_prev else None

    # Pass post_obj which now includes the slug implicitly
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
        print("--- CREATE POST: Form Validated ---") # Debug
        print(f"--- CREATE POST: Received Title: {form.title.data}") # Debug
        print(f"--- CREATE POST: Received Body (from form): {form.body.data[:200]}...") # Debug Body

        new_slug = Post.generate_unique_slug(form.title.data)
        post = Post(title=form.title.data,
                    body=form.body.data, # Using the data from the form field
                    author=current_user,
                    slug=new_slug)
        db.session.add(post)
        try:
            db.session.commit()
            print("--- CREATE POST: DB Commit Successful ---") # Debug
            flash('Your post has been created!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"--- CREATE POST: DB Commit FAILED: {e}") # Debug
            flash(f'Database error on create: {e}', 'danger')
        return redirect(url_for('main.admin_dashboard'))
    elif request.method == 'POST':
        print(f"--- CREATE POST: Form Validation FAILED. Errors: {form.errors}") # Debug validation failure

    # --- ADD KEY TO RENDER_TEMPLATE ---
    return render_template('admin/create_edit_post.html',
                           title='Create New Post',
                           form=form,
                           legend='New Post',
                           tinymce_api_key=current_app.config['TINYMCE_API_KEY']) # Pass the key

@bp.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    post = db.get_or_404(Post, post_id)
    form = PostForm()
    if form.validate_on_submit():
        print("--- EDIT POST: Form Validated ---") # Debug
        print(f"--- EDIT POST: Received Title: {form.title.data}") # Debug
        print(f"--- EDIT POST: Received Body (from form): {form.body.data[:200]}...") # Debug Body

        original_title = post.title
        post.title = form.title.data
        post.body = form.body.data # Update body from form
        if post.title != original_title:
            post.slug = Post.generate_unique_slug(post.title)
            print(f"--- EDIT POST: Slug regenerated: {post.slug}") # Debug

        try:
            db.session.commit()
            print("--- EDIT POST: DB Commit Successful ---") # Debug
            flash('Your post has been updated!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"--- EDIT POST: DB Commit FAILED: {e}") # Debug
            flash(f'Database error on update: {e}', 'danger')
        return redirect(url_for('main.post', slug=post.slug))
    elif request.method == 'POST':
         print(f"--- EDIT POST: Form Validation FAILED. Errors: {form.errors}") # Debug validation failure

    elif request.method == 'GET':
        form.title.data = post.title
        # Populate textarea with existing body on GET
        form.body.data = post.body
        print("--- EDIT POST: Populating form for GET request ---") # Debug
        
    # --- ADD KEY TO RENDER_TEMPLATE ---
    return render_template('admin/create_edit_post.html',
                           title='Edit Post',
                           form=form,
                           legend='Edit Post',
                           tinymce_api_key=current_app.config['TINYMCE_API_KEY']) # Pass the key

@bp.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.admin_dashboard'))
