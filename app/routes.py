# app/routes.py
# FINAL CORRECTED Comprehensive version with Slugs, RTE Key, and Cloudinary Image Uploads

from flask import make_response
from datetime import datetime, timezone
# NEW IMPORT for Flask-Mail
from flask_mail import Message
# NEW IMPORT for mail instance and limiter from app package
from app import mail, limiter  # Assuming limiter is initialized in app.__init__

from feedgen.feed import FeedGenerator
from flask import Response, url_for, send_from_directory  # Added send_from_directory for robots.txt
from app.forms import (LoginForm, RegistrationForm, PostForm, CommentForm, ContactForm, RequestPasswordResetForm,
                       ResetPasswordForm)  # Ensured ResetPasswordForm is here

# --- Core Flask & Extension Imports ---
from flask import (render_template, flash, redirect, url_for, request,
                   Blueprint, current_app)
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from urllib.parse import urlsplit
from functools import wraps
import os
import re  # NEW IMPORT for basic striptags/truncate in RSS

# --- App Specific Imports ---
from app import db
from app.models import User, Post, Comment, Tag  # Ensure Post model has slug, image_url, AND image_public_id fields

# --- Image Handling Imports ---
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

# cloudinary.api might be needed if using advanced API features, but uploader.destroy is sufficient for deletion

# --- Create Blueprint ---
bp = Blueprint('main', __name__)


# === Helper Functions ===

# --- Decorator for Admin Routes ---
def admin_required(f):
    """Ensures the user is logged in and is an admin."""

    @wraps(f)
    @login_required  # Apply login_required first
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function


# --- Helper function to upload to Cloudinary (MODIFIED for public_id) ---
def upload_to_cloudinary(file_to_upload):
    """
    Uploads a file to Cloudinary if configured.
    Returns (secure_url, public_id) on success, (None, None) on failure or if not configured.
    """
    if not file_to_upload:
        return None, None
    if not current_app.config.get('CLOUDINARY_CLOUD_NAME'):
        current_app.logger.warning("Upload Helper: Cloudinary not configured in Flask app.")
        flash("Image upload service is not configured.", "warning")
        return None, None

    filename = secure_filename(file_to_upload.filename)
    if not filename:
        current_app.logger.warning("Upload Helper: Invalid filename after sanitizing.")
        flash("Invalid image filename.", "warning")
        return None, None

    current_app.logger.info(f"Upload Helper: Attempting to upload '{filename}'")

    try:
        options = {
            'folder': "fragrance_blog",
            'resource_type': 'auto'
        }
        upload_result = cloudinary.uploader.upload(file_to_upload, **options)
        secure_url = upload_result.get('secure_url')
        public_id = upload_result.get('public_id')

        if secure_url and public_id:
            current_app.logger.info(f"Upload Helper: Success! URL: {secure_url}, Public ID: {public_id}")
            return secure_url, public_id
        else:
            current_app.logger.error(f"Upload Helper: Failed - No secure_url or public_id. Result: {upload_result}")
            flash("Image upload failed to return a valid URL or ID.", "danger")
            return None, None
    except Exception as e:
        current_app.logger.error(f"Upload Helper: Cloudinary upload FAILED with exception: {e}", exc_info=True)
        flash(f"Image upload encountered an error. Please try again later.", "danger")
        return None, None


# === End of upload_to_cloudinary function ===

# --- Helper functions for RSS feed text processing ---
def custom_striptags(html_string):
    if not html_string: return ""
    return re.sub(r'<[^>]+>', '', str(html_string))


def custom_truncate(text, length=300, end='...'):
    if not text: return ""
    text_str = str(text)
    if len(text_str) <= length:
        return text_str
    return text_str[:length - len(end)] + end


# === Public Routes ===

@bp.route('/')
@bp.route('/index')
def index():
    """Displays the homepage with paginated posts."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('POSTS_PER_PAGE', 5)  # Example: Make posts per page configurable
    query = sa.select(Post).order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    next_url = url_for('main.index', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.index', page=pagination.prev_num) if pagination.has_prev else None

    return render_template('index.html', title='Home', posts=posts,
                           next_url=next_url, prev_url=prev_url, pagination=pagination)


@bp.route('/post/<string:slug>', methods=['GET', 'POST'])
def post(slug):
    """Displays a single post by its slug and handles comment submission."""
    post_obj = db.session.scalar(sa.select(Post).filter_by(slug=slug))

    if post_obj is None:
        flash(f'Post "{slug}" not found.', 'warning')
        current_app.logger.warning(f"Attempt to access non-existent post with slug: {slug}")
        return redirect(url_for('main.index'))

    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('You must be logged in to comment.', 'warning')
            return redirect(url_for('main.login', next=url_for('main.post', slug=post_obj.slug)))

        comment = Comment(body=form.body.data, commenter=current_user, post=post_obj)
        db.session.add(comment)
        try:
            db.session.commit()
            flash('Your comment has been published.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving comment. Please try again.', 'danger')  # Simplified user message
            current_app.logger.error(f"DB Error saving comment for post {post_obj.id} (slug: {slug}): {e}",
                                     exc_info=True)
        return redirect(url_for('main.post', slug=post_obj.slug))

    page = request.args.get('page', 1, type=int)
    per_page_comments = current_app.config.get('COMMENTS_PER_PAGE', 10)
    comments_query = sa.select(Comment).where(Comment.post_id == post_obj.id).order_by(Comment.timestamp.desc())
    pagination_comments = db.paginate(comments_query, page=page, per_page=per_page_comments, error_out=False)
    comments = pagination_comments.items

    next_url_comments = url_for('main.post', slug=slug,
                                page=pagination_comments.next_num) if pagination_comments.has_next else None
    prev_url_comments = url_for('main.post', slug=slug,
                                page=pagination_comments.prev_num) if pagination_comments.has_prev else None

    return render_template('post.html', title=post_obj.title, post=post_obj, form=form,
                           comments=comments, next_url_comments=next_url_comments, prev_url_comments=prev_url_comments,
                           pagination_comments=pagination_comments)


@bp.route('/search')
def search():
    """Handles post search queries."""
    query_param = request.args.get('q', '', type=str).strip()

    if not query_param:
        flash("Please enter a search term.", "info")
        # Optionally redirect to index or show search page with a message
        return render_template('search_results.html', title="Search", query=query_param, posts=[], pagination=None)

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('SEARCH_RESULTS_PER_PAGE', 10)
    search_term = f"%{query_param}%"
    query = sa.select(Post).where(
        sa.or_(
            Post.title.ilike(search_term),
            Post.body.ilike(search_term)  # Be mindful of searching large TEXT fields for performance
        )
    ).order_by(Post.timestamp.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    next_url = url_for('main.search', q=query_param, page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.search', q=query_param, page=pagination.prev_num) if pagination.has_prev else None

    return render_template('search_results.html',
                           title=f"Search Results for '{query_param}'",
                           query=query_param,
                           posts=posts,
                           next_url=next_url,
                           prev_url=prev_url,
                           pagination=pagination)


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Displays contact form and handles submission by sending an email."""
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        sender_email = form.email.data
        subject_from_form = form.subject.data
        message_body = form.message.data

        admin_email_recipient = current_app.config.get('ADMIN_EMAIL')
        default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config.get('MAIL_USERNAME'))

        if not admin_email_recipient or not default_sender or not current_app.config.get('MAIL_SERVER'):
            current_app.logger.error(
                "Mail (ADMIN_EMAIL, MAIL_DEFAULT_SENDER, or MAIL_SERVER) not configured. Cannot send contact message.")
            flash("Sorry, the contact form is currently unavailable. Please try again later.", 'danger')
            current_app.logger.info(
                f"DEV MODE: Contact form submission (mail not configured):\nName: {name}\nEmail: {sender_email}\nSubject: {subject_from_form}\nMessage: {message_body}")
        else:
            msg = Message(
                subject=f"[{current_app.config.get('BLOG_NAME', 'Fragrance Blog')} Contact] {subject_from_form}",
                sender=default_sender,
                recipients=[admin_email_recipient],
                reply_to=sender_email
            )
            msg.body = f"""
You have received a new message from your blog contact form:

Name: {name}
Email: {sender_email}
Subject: {subject_from_form}

Message:
{message_body}
---
Reply directly to {sender_email}.
"""
            try:
                mail.send(msg)
                current_app.logger.info(f"Contact form email sent from {sender_email} to {admin_email_recipient}")
                flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            except Exception as e:
                current_app.logger.error(f"Failed to send contact form email from {sender_email}: {e}", exc_info=True)
                flash(
                    "Sorry, we couldn't send your message at this time due to a server error. Please try again later.",
                    'danger')

        return redirect(url_for('main.contact'))

    return render_template('contact.html', title='Contact Us', form=form)


# === Authentication Routes ===

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(lambda:
current_app.config.get('LOGIN_RATE_LIMIT', "5 per minute;100 per day"))
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('main.login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        flash('Login successful!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# --- Password Reset Helper Function ---
def send_password_reset_email_helper(user_obj):  # Renamed to avoid conflict if 'user' is used elsewhere
    """Generates reset token and sends password reset email."""
    token = user_obj.get_reset_password_token()

    msg = Message(
        subject=f"[{current_app.config.get('BLOG_NAME', 'Fragrance Blog')}] Password Reset Request",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config.get('MAIL_USERNAME')),
        recipients=[user_obj.email]
    )
    msg.body = f"""Dear {user_obj.username},

To reset your password, please visit the following link:
{url_for('main.reset_password', token=token, _external=True)}

If you did not request this reset, please ignore this email.
This link will expire in {current_app.config.get('PASSWORD_RESET_EXPIRES_SEC', 1800) // 60} minutes.

Sincerely,
The Blog Team
"""
    # msg.html = render_template('email/reset_password_email.html', user=user_obj, token=token) # For HTML email

    try:
        if current_app.config.get('MAIL_SERVER'):
            mail.send(msg)
            current_app.logger.info(f"Password reset email successfully sent to {user_obj.email}")
        else:
            current_app.logger.warning(
                f"Mail server not configured. Password reset email for {user_obj.email} NOT sent.")
            reset_url = url_for('main.reset_password', token=token, _external=True)
            current_app.logger.info(f"DEV MODE: Password Reset Link for {user_obj.email}: {reset_url}")
            # Flash message for dev mode is good for user feedback
            flash("Mail server not configured. For development, check console for reset link.", "info")

    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {user_obj.email}: {e}", exc_info=True)
        # Avoid flashing specific error, as it might reveal system state. Log is sufficient.
        flash('Sorry, we encountered an issue sending the password reset email. Please try again later.', 'danger')


@bp.route('/reset_password_request', methods=['GET', 'POST'])
@limiter.limit(lambda: current_app.config.get('PASSWORD_RESET_RATE_LIMIT', "3 per hour;10 per day"))
def reset_password_request():
    """Handles request to reset password (sends email with token)."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user_obj = db.session.scalar(sa.select(User).filter_by(email=form.email.data))  # Renamed
        if user_obj:
            send_password_reset_email_helper(user_obj)  # Call the helper
        # Always show the same message for security reasons
        flash('If an account with that email address exists, instructions to reset your password have been sent.',
              'info')
        return redirect(url_for('main.login'))

    return render_template('reset_password_request.html',
                           title='Request Password Reset', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset after token verification."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user_obj = User.verify_reset_password_token(token)  # Renamed
    if not user_obj:
        flash('That is an invalid or expired token. Please request a new one.', 'warning')
        return redirect(url_for('main.reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_obj.set_password(form.password.data)
        try:
            db.session.commit()
            flash('Your password has been successfully reset! You can now log in.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while resetting your password. Please try again.', 'danger')
            current_app.logger.error(f"DB Error resetting password for user {user_obj.id}: {e}", exc_info=True)

    return render_template('reset_password.html', title='Reset Your Password', form=form)


# === User Management Routes (Admin Only) ===

@bp.route('/admin/register', methods=['GET', 'POST'])
@admin_required
def register():
    """Handles new user registration (admin only)."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.is_admin = False  # Admins create non-admin users by default
        db.session.add(user)
        try:
            db.session.commit()
            flash(f'User {user.username} created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user {user.username}. Please check the logs.', 'danger')
            current_app.logger.error(f"DB Error creating user {user.username}: {e}", exc_info=True)
        return redirect(url_for('main.admin_dashboard'))

    return render_template('register.html', title='Register New User', form=form)


# === Admin Routes ===

@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Displays the admin dashboard with posts to manage."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ADMIN_POSTS_PER_PAGE', 10)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    next_url = url_for('main.admin_dashboard', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.admin_dashboard', page=pagination.prev_num) if pagination.has_prev else None

    return render_template('admin/dashboard.html', title='Admin Dashboard', posts=posts,
                           next_url=next_url, prev_url=prev_url, pagination=pagination)


@bp.route('/admin/post/new', methods=['GET', 'POST'])
@admin_required
def create_post():
    """Handles creation of a new blog post, including tags and Cloudinary image public_id."""
    form = PostForm()
    if form.validate_on_submit():
        current_app.logger.info("CREATE POST: Form Validated")

        image_file = form.image.data
        image_url = None
        image_public_id = None

        if image_file:
            current_app.logger.info("CREATE POST: Image file detected, attempting upload.")
            image_url, image_public_id = upload_to_cloudinary(image_file)
            if image_url is None:
                flash("Image upload failed, post will be created without image.", "warning")

        new_slug = Post.generate_unique_slug(form.title.data)
        post_obj = Post(title=form.title.data,  # Renamed to post_obj
                        body=form.body.data,
                        author=current_user,
                        slug=new_slug,
                        image_url=image_url,
                        image_public_id=image_public_id)

        tag_string = form.tags.data
        current_tags = set()
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
            for tag_name in tag_names:
                if not tag_name: continue
                tag_obj = db.session.scalar(sa.select(Tag).filter_by(name=tag_name))  # Renamed
                if tag_obj is None:
                    tag_obj = Tag(name=tag_name)
                    db.session.add(tag_obj)
                    current_app.logger.info(f"CREATE POST: Adding new tag '{tag_name}'")
                else:
                    current_app.logger.info(f"CREATE POST: Found existing tag '{tag_name}'")
                current_tags.add(tag_obj)
        post_obj.tags = list(current_tags)
        current_app.logger.info(f"CREATE POST: Final tags for post: {[t.name for t in post_obj.tags]}")

        db.session.add(post_obj)
        try:
            db.session.commit()
            current_app.logger.info(f"CREATE POST: DB Commit Successful for post '{post_obj.title}'")
            flash('Your post has been created!', 'success')
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"CREATE POST: DB Commit FAILED for post '{form.title.data}': {e}", exc_info=True)
            flash(f'Database error prevented post creation. Please try again.', 'danger')

    elif request.method == 'POST':
        current_app.logger.warning(f"CREATE POST: Form Validation FAILED. Errors: {form.errors}")

    return render_template('admin/create_edit_post.html',
                           title='Create New Post',
                           form=form,
                           legend='New Post',
                           tinymce_api_key=current_app.config.get('TINYMCE_API_KEY'))


@bp.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    """Handles editing of an existing blog post, including tags and Cloudinary image management."""
    post_to_edit = db.get_or_404(Post, post_id)
    form = PostForm()

    if form.validate_on_submit():
        current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: Form Validated")

        remove_image_checked = request.form.get('remove_image') == 'on'
        image_file = form.image.data
        old_public_id = post_to_edit.image_public_id

        if remove_image_checked:
            current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: Remove image checkbox checked.")
            if old_public_id and current_app.config.get('CLOUDINARY_CLOUD_NAME'):
                try:
                    cloudinary.uploader.destroy(old_public_id)
                    current_app.logger.info(
                        f"EDIT POST ID {post_to_edit.id}: Successfully deleted old image (public_id: {old_public_id}) from Cloudinary.")
                except Exception as e:
                    current_app.logger.error(
                        f"EDIT POST ID {post_to_edit.id}: Failed to delete old Cloudinary image (public_id: {old_public_id}): {e}",
                        exc_info=True)
                    flash("Failed to remove old image from storage.", "warning")
            elif old_public_id:
                current_app.logger.warning(
                    f"EDIT POST ID {post_to_edit.id}: Cloudinary not configured, skipping deletion of old image (public_id: {old_public_id}).")
            post_to_edit.image_url = None
            post_to_edit.image_public_id = None
            flash("Existing image has been removed from the post.", "info")  # More specific flash
        elif image_file:
            current_app.logger.info(
                f"EDIT POST ID {post_to_edit.id}: New image file '{secure_filename(image_file.filename)}' detected, attempting upload.")
            new_url, new_public_id = upload_to_cloudinary(image_file)
            if new_url and new_public_id:
                if old_public_id and old_public_id != new_public_id and current_app.config.get('CLOUDINARY_CLOUD_NAME'):
                    try:
                        cloudinary.uploader.destroy(old_public_id)
                        current_app.logger.info(
                            f"EDIT POST ID {post_to_edit.id}: Successfully deleted replaced image (public_id: {old_public_id}) from Cloudinary.")
                    except Exception as e:
                        current_app.logger.error(
                            f"EDIT POST ID {post_to_edit.id}: Failed to delete replaced Cloudinary image (public_id: {old_public_id}): {e}",
                            exc_info=True)
                        flash("Failed to remove previously uploaded image from storage.", "warning")
                elif old_public_id and old_public_id != new_public_id:
                    current_app.logger.warning(
                        f"EDIT POST ID {post_to_edit.id}: Cloudinary not configured, skipping deletion of replaced image (public_id: {old_public_id}).")
                post_to_edit.image_url = new_url
                post_to_edit.image_public_id = new_public_id
                current_app.logger.info(
                    f"EDIT POST ID {post_to_edit.id}: Updating image URL to '{new_url}' and public_id to '{new_public_id}'")
            else:
                flash("New image upload failed. Existing image (if any) was retained.", "warning")

        post_to_edit.tags.clear()
        tag_string = form.tags.data
        current_tags = set()
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
            for tag_name in tag_names:
                if not tag_name: continue
                tag_obj = db.session.scalar(sa.select(Tag).filter_by(name=tag_name))  # Renamed
                if tag_obj is None:
                    tag_obj = Tag(name=tag_name)
                    db.session.add(tag_obj)
                    current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: Adding new tag '{tag_name}'")
                else:
                    current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: Found existing tag '{tag_name}'")
                current_tags.add(tag_obj)
        post_to_edit.tags = list(current_tags)
        current_app.logger.info(
            f"EDIT POST ID {post_to_edit.id}: Final tags for post: {[t.name for t in post_to_edit.tags]}")

        original_title = post_to_edit.title
        post_to_edit.title = form.title.data
        post_to_edit.body = form.body.data
        if post_to_edit.title != original_title:  # Regenerate slug only if title changed
            old_slug = post_to_edit.slug
            post_to_edit.slug = Post.generate_unique_slug(post_to_edit.title)  # Ensure Post model has this method
            current_app.logger.info(
                f"EDIT POST ID {post_to_edit.id}: Slug regenerated from '{old_slug}' to '{post_to_edit.slug}'")

        try:
            db.session.commit()
            current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: DB Commit Successful")
            flash('Your post has been updated!', 'success')
            return redirect(url_for('main.post', slug=post_to_edit.slug))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"EDIT POST: DB Commit FAILED for post ID {post_to_edit.id}: {e}", exc_info=True)
            flash(f'Database error prevented post update. Please try again.', 'danger')

    elif request.method == 'POST':
        current_app.logger.warning(f"EDIT POST ID {post_to_edit.id}: Form Validation FAILED. Errors: {form.errors}")

    if request.method == 'GET':
        form.title.data = post_to_edit.title
        form.body.data = post_to_edit.body
        form.tags.data = ', '.join([tag.name for tag in post_to_edit.tags])
        current_app.logger.info(f"EDIT POST ID {post_to_edit.id}: Populating form for GET request")

    return render_template('admin/create_edit_post.html',
                           title='Edit Post',
                           form=form,
                           legend='Edit Post',
                           tinymce_api_key=current_app.config.get('TINYMCE_API_KEY'),
                           post=post_to_edit)


@bp.route('/tag/<string:tag_name>')
def tag(tag_name):
    """Displays posts associated with a specific tag."""
    tag_obj = db.session.scalar(sa.select(Tag).filter_by(name=tag_name.lower()))
    if tag_obj is None:
        flash(f'Tag "{tag_name}" not found.', 'warning')
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('TAG_POSTS_PER_PAGE', 5)

    # Using the relationship directly for pagination
    query = tag_obj.posts.order_by(Post.timestamp.desc())  # This should be a query object
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    posts_on_page = pagination.items  # Renamed for clarity

    next_url = url_for('main.tag', tag_name=tag_name, page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.tag', tag_name=tag_name, page=pagination.prev_num) if pagination.has_prev else None

    return render_template('tag_posts.html', tag=tag_obj, posts=posts_on_page,
                           title=f"Posts tagged '{tag_obj.name}'",
                           next_url=next_url, prev_url=prev_url, pagination=pagination)


@bp.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    """Handles deletion of a blog post and its Cloudinary image."""
    if request.method == 'POST':  # Redundant due to methods=['POST'] but safe
        post_to_delete = db.get_or_404(Post, post_id)
        post_title = post_to_delete.title
        image_public_id_to_delete = post_to_delete.image_public_id

        try:
            if image_public_id_to_delete and current_app.config.get('CLOUDINARY_CLOUD_NAME'):
                try:
                    cloudinary.uploader.destroy(image_public_id_to_delete)
                    current_app.logger.info(
                        f"DELETE POST: Successfully deleted image (public_id: {image_public_id_to_delete}) from Cloudinary for post {post_id}")
                except Exception as img_del_e:
                    current_app.logger.error(
                        f"DELETE POST: Failed to delete Cloudinary image for post {post_id} (public_id: {image_public_id_to_delete}): {img_del_e}",
                        exc_info=True)
                    flash("Post deleted from database, but failed to remove associated image from Cloudinary.",
                          "warning")
            elif image_public_id_to_delete:
                current_app.logger.warning(
                    f"DELETE POST: Cloudinary not configured, skipping deletion of image (public_id: {image_public_id_to_delete}) for post {post_id}.")

            db.session.delete(post_to_delete)
            db.session.commit()
            flash(f'Post "{post_title}" has been deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting post "{post_title}". Please try again.', 'danger')
            current_app.logger.error(f"DB Error deleting post {post_id} ('{post_title}'): {e}", exc_info=True)
    else:
        flash('Invalid request method for deleting post.', 'warning')
        current_app.logger.warning(f"Invalid method '{request.method}' for deleting post {post_id}.")

    return redirect(url_for('main.admin_dashboard'))


@bp.route('/feed.xml')
def rss_feed():
    """Generates the RSS feed for the blog."""
    fg = FeedGenerator()

    blog_name = current_app.config.get('BLOG_NAME', 'My Fragrance Blog')
    blog_author_name = current_app.config.get('BLOG_AUTHOR_NAME', 'Blog Admin')
    blog_author_email = current_app.config.get('BLOG_AUTHOR_EMAIL', 'noreply@example.com')
    posts_for_feed = current_app.config.get('RSS_FEED_POST_LIMIT', 20)

    fg.id(request.url_root)
    fg.title(f'{blog_name} - Latest Posts')
    fg.link(href=url_for('main.index', _external=True), rel='alternate')
    fg.subtitle(current_app.config.get('BLOG_SUBTITLE', 'Reviews, musings, and guides on the world of scents.'))
    fg.language(current_app.config.get('BLOG_LANGUAGE', 'en'))
    fg.author({'name': blog_author_name, 'email': blog_author_email})
    fg.link(href=url_for('main.rss_feed', _external=True), rel='self')

    latest_posts = db.session.scalars(
        sa.select(Post).order_by(Post.timestamp.desc()).limit(posts_for_feed)
    ).all()

    for post_item in latest_posts:
        fe = fg.add_entry()
        entry_url = url_for('main.post', slug=post_item.slug, _external=True)
        fe.id(entry_url)
        fe.title(post_item.title)
        fe.link(href=entry_url)

        # Use helper functions for stripping HTML and truncating
        stripped_body = custom_striptags(post_item.body)
        summary = custom_truncate(stripped_body, length=300, end='...')
        fe.summary(summary)
        # fe.content(post_item.body, type='html') # Optionally include full HTML content

        fe.pubDate(post_item.timestamp)  # Ensure timestamp is timezone-aware for consistency
        if post_item.author:  # Add post author if available
            fe.author({'name': post_item.author.username})

    rss_feed_xml = fg.rss_str(pretty=True)
    return Response(rss_feed_xml, mimetype='application/rss+xml')


# Route to serve robots.txt from the static folder
@bp.route('/robots.txt')
def serve_robots_txt():
    return send_from_directory(current_app.static_folder, 'robots.txt')


@bp.route('/sitemap.xml')
def sitemap():
    """Generates an XML sitemap for search engines."""

    # Initialize a list to hold all page data for the sitemap
    pages_for_sitemap = []

    # --- Define and add STATIC pages ---
    static_page_definitions = [
        {'endpoint': 'main.index', 'priority': '1.0', 'changefreq': 'daily'},
        {'endpoint': 'main.contact', 'priority': '0.7', 'changefreq': 'monthly'},
        # Example: {'endpoint': 'main.about', 'priority': '0.6', 'changefreq': 'yearly'}, # If you add an 'about' page
    ]
    for page_def in static_page_definitions:
        try:  # Add try-except around url_for in case a route is temporarily undefined
            pages_for_sitemap.append({
                'loc': url_for(page_def['endpoint'], _external=True),
                'lastmod': datetime.now(timezone.utc).strftime("%Y-%m-%d"),  # Current date for static pages
                'priority': page_def['priority'],
                'changefreq': page_def['changefreq']
            })
        except Exception as e:
            current_app.logger.error(f"Error generating URL for static sitemap page '{page_def['endpoint']}': {e}",
                                     exc_info=True)

    # --- Add DYNAMIC pages: Blog Posts ---
    try:
        posts = db.session.scalars(sa.select(Post).order_by(Post.timestamp.desc())).all()
        for post_item in posts:
            try:  # Add try-except for individual post URL generation
                pages_for_sitemap.append({
                    'loc': url_for('main.post', slug=post_item.slug, _external=True),
                    'lastmod': post_item.timestamp.strftime("%Y-%m-%d"),  # Use the post's actual timestamp
                    'priority': '0.9',
                    'changefreq': 'weekly'
                })
            except Exception as e:
                current_app.logger.error(
                    f"Error generating URL for sitemap post (ID: {post_item.id}, Slug: {post_item.slug}): {e}",
                    exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error fetching posts for sitemap: {e}", exc_info=True)

    # --- Add DYNAMIC pages: Tags ---
    try:
        tags = db.session.scalars(sa.select(Tag).order_by(Tag.name)).all()
        for tag_item in tags:
            try:  # Add try-except for individual tag URL generation
                # Optional: Only include tags that actually have posts associated.
                # post_count = db.session.query(post_tags.c.post_id).filter_by(tag_id=tag_item.id).count()
                # if post_count > 0:
                pages_for_sitemap.append({
                    'loc': url_for('main.tag', tag_name=tag_item.name, _external=True),
                    'lastmod': datetime.now(timezone.utc).strftime("%Y-%m-%d"),  # Or find newest post with this tag
                    'priority': '0.5',
                    'changefreq': 'weekly'
                })
            except Exception as e:
                current_app.logger.error(
                    f"Error generating URL for sitemap tag (ID: {tag_item.id}, Name: {tag_item.name}): {e}",
                    exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error fetching tags for sitemap: {e}", exc_info=True)

    # --- Render the XML template with the collected pages ---
    sitemap_xml_content = render_template('sitemap_template.xml', pages=pages_for_sitemap)

    # --- Create and return the XML response ---
    response = make_response(sitemap_xml_content)
    response.headers["Content-Type"] = "application/xml"

    current_app.logger.info("Sitemap.xml generated successfully with %s URLs.", len(pages_for_sitemap))
    return response
# === End of routes.py ===
