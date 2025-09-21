from flask import make_response, jsonify
from datetime import datetime, timezone
from flask_mail import Message
from app import mail, limiter, db
from feedgen.feed import FeedGenerator
from flask import Response, send_from_directory
from app.forms import (LoginForm, RegistrationForm, PostForm, CommentForm, ReplyForm,
                       ContactForm, RequestPasswordResetForm,
                       ResetPasswordForm, ChangePasswordForm, EditCommentForm,
                       SubscriptionForm, ChangeUsernameForm)

# --- Core Flask & Extension Imports ---
from flask import (render_template, flash, redirect, url_for, request,
                   Blueprint, current_app)
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from functools import wraps
import re

# --- App Specific Imports ---
from app.models import User, Post, Comment, Tag, Subscriber

# --- Image Handling Imports ---
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader


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

def send_confirmation_email(user):
    """Generates a confirmation token and sends the email."""
    token = user.get_reset_password_token()
    msg = Message(
        subject=f"[{current_app.config.get('BLOG_NAME')}] Please Confirm Your Email",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[user.email]
    )
    msg.body = f"""Dear {user.username},

Welcome to {current_app.config.get('BLOG_NAME')}!

To confirm your account and complete your registration, please click the following link:
{url_for('main.confirm_email', token=token, _external=True)}

If you did not sign up for an account, please ignore this email.

Sincerely,
The Liquid Blossom Team
"""
    mail.send(msg)

def upload_to_cloudinary(file_to_upload):
    """
    Uploads a file to Cloudinary if configured.
    Returns (secure_url, public_id) on success, (None, None) on failure or if not configured.
    """
    if not file_to_upload:
        return None, None
    if not current_app.config.get('CLOUDINARY_CLOUD_NAME'):
        current_app.logger.warning(
            "Upload Helper: Cloudinary not configured in Flask app.")
        flash("Image upload service is not configured.", "warning")
        return None, None

    filename = secure_filename(file_to_upload.filename)
    if not filename:
        current_app.logger.warning(
            "Upload Helper: Invalid filename after sanitizing.")
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
            current_app.logger.info(
                f"Upload Helper: Success! URL: {secure_url}, Public ID: {public_id}")
            return secure_url, public_id
        else:
            current_app.logger.error(
                f"Upload Helper: Failed - No secure_url or public_id. Result: {upload_result}")
            flash("Image upload failed to return a valid URL or ID.", "danger")
            return None, None
    except Exception as e:
        current_app.logger.error(
            f"Upload Helper: Cloudinary upload FAILED with exception: {e}",
            exc_info=True)
        flash(f"Image upload encountered an error. Please try again later.",
              "danger")
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


# === Health Check Route for Pinger Operation===
@bp.route('/healthz')
@limiter.exempt
def health_check():
    """
    A basic endpoint for uptime monitoring services
    to hit. It just returns a '200 OK' response aka I AM ALIVE.
    Added exemption :)
    """
    return "OK", 200


@bp.before_app_request
def before_request():
    """Redirects unconfirmed users away from protected pages."""
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.blueprint == 'main' \
            and request.endpoint not in ['main.confirm_email', 'main.resend_confirmation', 'main.logout', 'main.unconfirmed', 'static']:
        return redirect(url_for('main.unconfirmed'))

# === Public Routes ===

@bp.route('/')
@bp.route('/index')
def index():
    """Displays the homepage with paginated posts."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('POSTS_PER_PAGE', 5)
    query = sa.select(Post).where(Post.status == True,
                                  Post.published_at != None).order_by(
        Post.published_at.desc())
    pagination = db.paginate(query, page=page, per_page=per_page,
                             error_out=False)
    posts = pagination.items

    next_url = url_for('main.index',
                       page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.index',
                       page=pagination.prev_num) if pagination.has_prev else None

    return render_template('index.html', title='Home', posts=posts,
                           next_url=next_url, prev_url=prev_url,
                           pagination=pagination)


@bp.route('/post/<string:slug>', methods=['GET', 'POST'])
def post(slug):
    """Displays a single post and handles comment and reply submissions."""
    post_obj = db.session.scalar(sa.select(Post).filter_by(slug=slug))

    if post_obj is None or (not post_obj.status and not (
            current_user.is_authenticated and current_user.is_admin)):
        flash('Post not found or is currently a draft.', 'warning')
        return redirect(url_for('main.index'))

    comment_form = CommentForm()
    reply_form = ReplyForm()

    # --- Logic to handle a new REPLY submission ---
    if reply_form.validate_on_submit() and reply_form.submit.data:
        if not current_user.is_authenticated:
            flash('You must be logged in to reply.', 'warning')
            return redirect(url_for('main.login', next=request.url))

        parent_comment = db.session.get(Comment, int(reply_form.parent_id.data))
        if parent_comment:
            reply = Comment(body=reply_form.body.data,
                            commenter=current_user,
                            post=post_obj,
                            parent=parent_comment)
            db.session.add(reply)
            db.session.commit()
            flash('Your reply has been posted.', 'success')
        else:
            flash('Parent comment not found.', 'danger')
        return redirect(url_for('main.post', slug=post_obj.slug))

    # --- Logic to handle a new top-level COMMENT submission ---
    if comment_form.validate_on_submit() and comment_form.submit.data:
        if not current_user.is_authenticated:
            flash('You must be logged in to comment.', 'warning')
            return redirect(url_for('main.login', next=request.url))

        comment = Comment(body=comment_form.body.data,
                          commenter=current_user,
                          post=post_obj)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.', 'success')
        return redirect(url_for('main.post', slug=post_obj.slug))


# === Public User Registration Route ===

@bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def signup():
    """Handles public user registration and sends confirmation email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    # 'form.validate_on_submit()' now handles the ReCaptcha check automatically.
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=False, # This is a righteous default
            confirmed=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        send_confirmation_email(user)
        flash('A confirmation email has been sent. Please check your inbox.', 'success')
        return redirect(url_for('main.login'))
    return render_template('signup.html', title='Sign Up', form=form)


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Displays contact form and handles submission by sending an email."""
    form = ContactForm()
    if form.validate_on_submit():
        if form.honeypot.data:
            current_app.logger.warning(f"Honeypot field filled by IP: {request.remote_addr}")
            flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            return redirect(url_for('main.index'))
        name = form.name.data
        sender_email = form.email.data
        subject_from_form = form.subject.data
        message_body = form.message.data

        admin_email_recipient = current_app.config.get('ADMIN_EMAIL')
        mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        mail_server = current_app.config.get('MAIL_SERVER')

        if not all([admin_email_recipient, mail_default_sender, mail_server]):
            current_app.logger.error(
                "Mail configuration is incomplete. Cannot send contact email.")
            flash(
                "The mail service is not configured correctly. Please contact the administrator directly.",
                'danger')
            return redirect(url_for('main.contact'))

        msg = Message(
            subject=f"[{current_app.config.get('BLOG_NAME', 'Fragrance Blog')} Contact] {subject_from_form}",
            sender=mail_default_sender,
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
            current_app.logger.info(
                f"Contact form email sent from {sender_email} to {admin_email_recipient}")
            flash(
                'Your message has been sent successfully! We will get back to you soon.',
                'success')
        except Exception as e:
            current_app.logger.error(
                f"Failed to send contact form email from {sender_email}: {e}",
                exc_info=True)
            flash(
                "Sorry, we couldn't send your message at this time due to a server error.",
                'danger')

        return redirect(url_for('main.contact'))

    return render_template('contact.html', title='Contact Us', form=form)

@bp.route('/privacy-policy')
def privacy_policy():
    """Displays the privacy policy page."""
    return render_template('privacy_policy.html', title='Privacy Policy')

@bp.route('/about')
def about():
    """Displays the about page."""
    return render_template('about.html', title='About')

# === NEWSLETTER SUBSCRIBE ROUTE ===
@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Handles newsletter subscription form submission."""
    form = SubscriptionForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        subscriber = Subscriber(email=email)
        try:
            db.session.add(subscriber)
            db.session.commit()
            flash('Thank you for subscribing!', 'success')
            current_app.logger.info(f"New newsletter subscriber: {email}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding subscriber {email}: {e}",
                                     exc_info=True)
            if 'UNIQUE constraint failed' in str(e):
                flash('This email address is already subscribed.', 'info')
            else:
                flash('An error occurred. Please try again.', 'danger')
    else:
        if form.email.errors:
            for error in form.email.errors:
                flash(error, 'danger')

    return redirect(request.referrer or url_for('main.index'))


# === Authentication Routes ===

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Handles user login, now with a check for email confirmation."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('main.login'))

        if not user.confirmed:
            flash(
                'Your account is not yet confirmed. Please check your email for a confirmation link.',
                'warning')
            return redirect(url_for('main.login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        flash('Login successful!', 'success')
        return redirect(next_page or url_for('main.index'))

    return render_template('login.html', title='Sign In', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/confirm/<token>')
@login_required
def confirm_email(token):
    """Handles the confirmation token from the user's email."""
    if current_user.confirmed:
        return redirect(url_for('main.index'))

    #verify_reset_password_token to validate a timed token.
    user = User.verify_reset_password_token(token)

    # Ensure the token belongs to the currently logged-in user.
    if user is None or user.id != current_user.id:
        flash('The confirmation link is invalid or has expired.', 'danger')
    else:
        current_user.confirmed = True
        current_user.confirmed_on = datetime.utcnow()
        db.session.commit()
        flash('You have successfully confirmed your account! Thanks!',
              'success')
    return redirect(url_for('main.index'))


@bp.route('/unconfirmed')
@login_required
def unconfirmed():
    """Page shown to logged-in but unconfirmed users."""
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('unconfirmed.html', title='Confirm Your Account')


@bp.route('/resend_confirmation')
@login_required
def resend_confirmation():
    """Route to resend the confirmation email."""
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    try:
        send_confirmation_email(current_user)
        flash('A new confirmation email has been sent to your email address.',
              'success')
    except Exception as e:
        current_app.logger.error(
            f"Error resending confirmation for {current_user.email}: {e}",
            exc_info=True)
        flash('There was an error sending the email. Please try again later.',
              'danger')
    return redirect(url_for('main.unconfirmed'))


# --- Password Reset Helper Function ---
def send_password_reset_email_helper(user_obj):
    """Generates reset token and sends password reset email."""
    token = user_obj.get_reset_password_token()
    msg = Message(
        subject=f"[{current_app.config.get('BLOG_NAME', 'Fragrance Blog')}] Password Reset Request",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER',
                                      current_app.config.get('MAIL_USERNAME')),
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
    try:
        if current_app.config.get('MAIL_SERVER'):
            mail.send(msg)
            current_app.logger.info(
                f"Password reset email successfully sent to {user_obj.email}")
        else:
            current_app.logger.warning(
                f"Mail server not configured. Password reset email for {user_obj.email} NOT sent.")
            reset_url = url_for('main.reset_password', token=token,
                                _external=True)
            current_app.logger.info(
                f"DEV MODE: Password Reset Link for {user_obj.email}: {reset_url}")
            flash(
                "Mail server not configured. For development, check console for reset link.",
                "info")
    except Exception as e:
        current_app.logger.error(
            f"Failed to send password reset email to {user_obj.email}: {e}",
            exc_info=True)
        flash(
            'Sorry, we encountered an issue sending the password reset email. Please try again later.',
            'danger')


@bp.route('/reset_password_request', methods=['GET', 'POST'])
@limiter.limit(lambda: current_app.config.get('PASSWORD_RESET_RATE_LIMIT',
                                              "3 per hour;10 per day"))
def reset_password_request():
    """Handles request to reset password (sends email with token)."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user_obj = db.session.scalar(
            sa.select(User).filter_by(email=form.email.data))
        if user_obj:
            send_password_reset_email_helper(user_obj)
        flash(
            'If an account with that email address exists, instructions to reset your password have been sent.',
            'info')
        return redirect(url_for('main.login'))

    return render_template('reset_password_request.html',
                           title='Request Password Reset', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset after token verification."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user_obj = User.verify_reset_password_token(token)
    if not user_obj:
        flash('That is an invalid or expired token. Please request a new one.',
              'warning')
        return redirect(url_for('main.reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_obj.set_password(form.password.data)
        try:
            db.session.commit()
            flash(
                'Your password has been successfully reset! You can now log in.',
                'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash(
                f'An error occurred while resetting your password. Please try again.',
                'danger')
            current_app.logger.error(
                f"DB Error resetting password for user {user_obj.id}: {e}",
                exc_info=True)

    return render_template('reset_password.html', title='Reset Your Password',
                           form=form)


# === User Management Routes (Admin Only) ===
@bp.route('/admin/register', methods=['GET', 'POST'])
@admin_required
def register():
    """Handles new user registration (admin only)."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.is_admin = False
        db.session.add(user)
        try:
            db.session.commit()
            flash(f'User {user.username} created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(
                f'Error creating user {user.username}. Please check the logs.',
                'danger')
            current_app.logger.error(
                f"DB Error creating user {user.username}: {e}", exc_info=True)
        return redirect(url_for('main.admin_dashboard'))

    return render_template('register.html', title='Register New User',
                           form=form)


# === Admin Routes ===
@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Displays the admin dashboard with posts to manage."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ADMIN_POSTS_PER_PAGE', 10)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=per_page,
                             error_out=False)
    posts = pagination.items

    next_url = url_for('main.admin_dashboard',
                       page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.admin_dashboard',
                       page=pagination.prev_num) if pagination.has_prev else None

    return render_template('admin/dashboard.html', title='Admin Dashboard',
                           posts=posts,
                           next_url=next_url, prev_url=prev_url,
                           pagination=pagination)


@bp.route('/admin/post/new', methods=['GET', 'POST'])
@admin_required
def create_post():
    """Handles creation of a new blog post."""
    form = PostForm()
    if form.validate_on_submit():
        image_file = form.image.data
        image_url, image_public_id = None, None
        if image_file:
            image_url, image_public_id = upload_to_cloudinary(image_file)
            if image_url is None:
                flash(
                    "Image upload failed, post will be created without an image.",
                    "warning")

        new_slug = Post.generate_unique_slug(form.title.data)
        post_obj = Post(title=form.title.data,
                        body=form.body.data,
                        author=current_user,
                        slug=new_slug,
                        image_url=image_url,
                        image_public_id=image_public_id,
                        status=form.status.data)

        if post_obj.status:
            post_obj.published_at = datetime.utcnow()

        tag_string = form.tags.data
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',')
                         if name.strip()]
            for tag_name in tag_names:
                tag_obj = db.session.scalar(
                    sa.select(Tag).filter_by(name=tag_name))
                if tag_obj is None:
                    tag_obj = Tag(name=tag_name)
                    db.session.add(tag_obj)
                post_obj.tags.append(tag_obj)

        db.session.add(post_obj)
        try:
            db.session.commit()
            flash('Your post has been created!', 'success')
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"CREATE POST: DB Commit FAILED: {e}",
                                     exc_info=True)
            flash('Database error prevented post creation. Please try again.',
                  'danger')

    return render_template('admin/create_edit_post.html',
                           title='Create New Post',
                           form=form, legend='New Post',
                           tinymce_api_key=current_app.config.get(
                               'TINYMCE_API_KEY'))


@bp.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    """Handles editing of an existing blog post."""
    post_to_edit = db.get_or_404(Post, post_id)
    form = PostForm()
    if form.validate_on_submit():
        remove_image_checked = request.form.get('remove_image') == 'on'
        image_file = form.image.data
        old_public_id = post_to_edit.image_public_id

        if remove_image_checked:
            if old_public_id and current_app.config.get(
                    'CLOUDINARY_CLOUD_NAME'):
                try:
                    cloudinary.uploader.destroy(old_public_id)
                except Exception as e:
                    current_app.logger.error(
                        f"Failed to delete old Cloudinary image {old_public_id}: {e}",
                        exc_info=True)
            post_to_edit.image_url = None
            post_to_edit.image_public_id = None
        elif image_file:
            new_url, new_public_id = upload_to_cloudinary(image_file)
            if new_url and new_public_id:
                if old_public_id and old_public_id != new_public_id and current_app.config.get(
                        'CLOUDINARY_CLOUD_NAME'):
                    try:
                        cloudinary.uploader.destroy(old_public_id)
                    except Exception as e:
                        current_app.logger.error(
                            f"Failed to delete replaced Cloudinary image {old_public_id}: {e}",
                            exc_info=True)
                post_to_edit.image_url = new_url
                post_to_edit.image_public_id = new_public_id
            else:
                flash("New image upload failed. Existing image was retained.",
                      "warning")

        post_to_edit.title = form.title.data
        post_to_edit.body = form.body.data
        if post_to_edit.is_modified('title'):
            post_to_edit.slug = Post.generate_unique_slug(post_to_edit.title)

        original_status = post_to_edit.status
        post_to_edit.status = form.status.data
        # If the post is being published for the first time
        if post_to_edit.status and not original_status:
            post_to_edit.published_at = datetime.utcnow()
        # If a post is being unpublished, remove its publish date
        elif not post_to_edit.status:
            post_to_edit.published_at = None

        post_to_edit.tags.clear()
        tag_string = form.tags.data
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',')
                         if name.strip()]
            for tag_name in tag_names:
                tag_obj = db.session.scalar(
                    sa.select(Tag).filter_by(name=tag_name))
                if tag_obj is None:
                    tag_obj = Tag(name=tag_name)
                    db.session.add(tag_obj)
                post_to_edit.tags.append(tag_obj)
        try:
            db.session.commit()
            flash('Your post has been updated!', 'success')
            return redirect(url_for('main.post', slug=post_to_edit.slug))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"EDIT POST: DB Commit FAILED for post ID {post_to_edit.id}: {e}",
                exc_info=True)
            flash('Database error prevented post update. Please try again.',
                  'danger')

    elif request.method == 'GET':
        form.title.data = post_to_edit.title
        form.body.data = post_to_edit.body
        form.tags.data = ', '.join([tag.name for tag in post_to_edit.tags])
        form.status.data = post_to_edit.status

    return render_template('admin/create_edit_post.html', title='Edit Post',
                           form=form,
                           legend='Edit Post',
                           tinymce_api_key=current_app.config.get(
                               'TINYMCE_API_KEY'), post=post_to_edit)


@bp.route('/tag/<string:tag_name>')
def tag(tag_name):
    """Displays posts associated with a specific tag."""
    tag_obj = db.session.scalar(sa.select(Tag).filter_by(name=tag_name.lower()))
    if tag_obj is None:
        flash(f'Tag "{tag_name}" not found.', 'warning')
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('TAG_POSTS_PER_PAGE', 5)
    query = sa.select(Post).join(Post.tags).where(Tag.id == tag_obj.id,
                                                  Post.status == True,
                                                  Post.published_at != None).order_by(
        Post.published_at.desc())
    pagination = db.paginate(query, page=page, per_page=per_page,
                             error_out=False)
    posts_on_page = pagination.items

    next_url = url_for('main.tag', tag_name=tag_name,
                       page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.tag', tag_name=tag_name,
                       page=pagination.prev_num) if pagination.has_prev else None

    return render_template('tag_posts.html', tag=tag_obj, posts=posts_on_page,
                           title=f"Posts tagged '{tag_obj.name}'",
                           next_url=next_url, prev_url=prev_url,
                           pagination=pagination)


@bp.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    """Handles deletion of a blog post and its Cloudinary image."""
    post_to_delete = db.get_or_404(Post, post_id)
    post_title = post_to_delete.title
    image_public_id_to_delete = post_to_delete.image_public_id

    try:
        if image_public_id_to_delete and current_app.config.get(
                'CLOUDINARY_CLOUD_NAME'):
            try:
                cloudinary.uploader.destroy(image_public_id_to_delete)
            except Exception as img_del_e:
                current_app.logger.error(
                    f"Failed to delete Cloudinary image for post {post_id}: {img_del_e}",
                    exc_info=True)
                flash(
                    "Post deleted, but failed to remove image from cloud storage.",
                    "warning")

        db.session.delete(post_to_delete)
        db.session.commit()
        flash(f'Post "{post_title}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting post "{post_title}". Please try again.',
              'danger')
        current_app.logger.error(
            f"DB Error deleting post {post_id} ('{post_title}'): {e}",
            exc_info=True)

    return redirect(url_for('main.admin_dashboard'))


@bp.route('/feed.xml')
def rss_feed():
    """Generates the RSS feed for the blog."""
    fg = FeedGenerator()

    blog_name = current_app.config.get('BLOG_NAME', 'My Fragrance Blog')
    blog_author_name = current_app.config.get('BLOG_AUTHOR_NAME', 'Blog Admin')
    blog_author_email = current_app.config.get('BLOG_AUTHOR_EMAIL',
                                               'noreply@example.com')
    posts_for_feed = current_app.config.get('RSS_FEED_POST_LIMIT', 20)

    fg.id(request.url_root)
    fg.title(f'{blog_name} - Latest Posts')
    fg.link(href=url_for('main.index', _external=True), rel='alternate')
    fg.subtitle(current_app.config.get('BLOG_SUBTITLE',
                                       'Reviews, musings, and guides on the world of scents.'))
    fg.language(current_app.config.get('BLOG_LANGUAGE', 'en'))
    fg.author({'name': blog_author_name, 'email': blog_author_email})
    fg.link(href=url_for('main.rss_feed', _external=True), rel='self')

    latest_posts = db.session.scalars(sa.select(Post).where(Post.status == True,
                                                            Post.published_at != None).order_by(
        Post.published_at.desc()).limit(20)).all()


    for post_item in latest_posts:
        fe = fg.add_entry()
        entry_url = url_for('main.post', slug=post_item.slug, _external=True)
        fe.id(entry_url)
        fe.title(post_item.title)
        fe.link(href=entry_url)
        stripped_body = custom_striptags(post_item.body)
        summary = custom_truncate(stripped_body, length=300, end='...')
        fe.summary(summary)
        fe.pubDate(post_item.timestamp)
        if post_item.author:
            fe.author({'name': post_item.author.username})

    rss_feed_xml = fg.rss_str(pretty=True)
    return Response(rss_feed_xml, mimetype='application/rss+xml')


@bp.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    """Allows a user to edit their own comment."""
    comment = db.get_or_404(Comment, comment_id)
    if comment.commenter != current_user and not current_user.is_admin:
        flash('You do not have permission to edit this comment.', 'danger')
        return redirect(url_for('main.post', slug=comment.post.slug))

    form = EditCommentForm()
    if form.validate_on_submit():
        comment.body = form.body.data
        try:
            db.session.commit()
            flash('Your comment has been updated.', 'success')
            return redirect(url_for('main.post', slug=comment.post.slug,
                                    _anchor=f'comment-{comment.id}'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating comment {comment_id}: {e}", exc_info=True)
            flash(
                'An error occurred while updating your comment. Please try again.',
                'danger')

    elif request.method == 'GET':
        form.body.data = comment.body

    return render_template('edit_comment.html', title='Edit Comment', form=form,
                           comment=comment)


@bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Allows a user to delete their own comment."""
    comment = db.get_or_404(Comment, comment_id)
    post_slug = comment.post.slug
    if comment.commenter != current_user and not current_user.is_admin:
        flash('You do not have permission to delete this comment.', 'danger')
        return redirect(url_for('main.post', slug=post_slug))

    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Your comment has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment {comment_id}: {e}",
                                 exc_info=True)
        flash('An error occurred while deleting your comment.', 'danger')

    return redirect(url_for('main.post', slug=post_slug))


@bp.route('/robots.txt')
def serve_robots_txt():
    return send_from_directory(current_app.static_folder, 'robots.txt')


# CORRECTED: Added logic to prevent empty searches
@bp.route('/search')
def search():
    """Handles post search queries, preventing empty searches."""
    query_param = request.args.get('q', '', type=str).strip()

    if not query_param:
        return render_template('search_results.html', title="Search", query='',
                               posts=[], pagination=None)

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('SEARCH_RESULTS_PER_PAGE', 10)
    search_term = f"%{query_param}%"

    query = sa.select(Post).where(
        Post.status == True,
        sa.or_(
            Post.title.ilike(search_term),
            Post.body.ilike(search_term)
        )
    ).order_by(Post.published_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page,
                             error_out=False)
    posts = pagination.items

    return render_template('search_results.html',
                           title=f"Search Results for '{query_param}'",
                           query=query_param,
                           posts=posts,
                           pagination=pagination)


@bp.route('/sitemap.xml')
def sitemap():
    """Generates an XML sitemap for search engines."""
    pages_for_sitemap = []

    static_page_definitions = [
        {'endpoint': 'main.index', 'priority': '1.0', 'changefreq': 'daily'},
        {'endpoint': 'main.contact', 'priority': '0.7',
         'changefreq': 'monthly'},
    ]
    for page_def in static_page_definitions:
        try:
            pages_for_sitemap.append({
                'loc': url_for(page_def['endpoint'], _external=True),
                'lastmod': datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                'priority': page_def['priority'],
                'changefreq': page_def['changefreq']
            })
        except Exception as e:
            current_app.logger.error(
                f"Error generating URL for static sitemap page '{page_def['endpoint']}': {e}")

    try:
        posts = db.session.scalars(
            sa.select(Post).order_by(Post.timestamp.desc())).all()
        for post_item in posts:
            pages_for_sitemap.append({
                'loc': url_for('main.post', slug=post_item.slug,
                               _external=True),
                'lastmod': post_item.timestamp.strftime("%Y-%m-%d"),
                'priority': '0.9',
                'changefreq': 'weekly'
            })
    except Exception as e:
        current_app.logger.error(f"Error fetching posts for sitemap: {e}",
                                 exc_info=True)

    try:
        tags = db.session.scalars(sa.select(Tag).order_by(Tag.name)).all()
        for tag_item in tags:
            pages_for_sitemap.append({
                'loc': url_for('main.tag', tag_name=tag_item.name,
                               _external=True),
                'lastmod': datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                'priority': '0.5',
                'changefreq': 'weekly'
            })
    except Exception as e:
        current_app.logger.error(f"Error fetching tags for sitemap: {e}",
                                 exc_info=True)

    sitemap_xml_content = render_template('sitemap_template.xml',
                                          pages=pages_for_sitemap)
    response = make_response(sitemap_xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response


# === ADMIN ACCOUNT MANAGEMENT ROUTE (CORRECTED) ===
# This first function just RENDERS the page
# === ADMIN ACCOUNT MANAGEMENT (REFACTORED) ===

# This first function just RENDERS the page
@bp.route('/admin/account', methods=['GET'])
@admin_required
def admin_account():
    """Renders the account management page."""
    password_form = ChangePasswordForm()
    username_form = ChangeUsernameForm(current_user.username)
    return render_template('admin/account.html',
                           title='Admin Account Management',
                           password_form=password_form,
                           username_form=username_form)


# This second function HANDLES the password change
@bp.route('/admin/account/change-password', methods=['POST'])
@admin_required
def change_password():
    """Handles password change form submission."""
    # We need to instantiate both forms in case of a validation error
    password_form = ChangePasswordForm()
    username_form = ChangeUsernameForm(current_user.username)

    if password_form.validate_on_submit():
        if current_user.check_password(password_form.current_password.data):
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash(
                'Password changed successfully. Please log in again for security.',
                'success')
            logout_user()
            return redirect(url_for('main.login'))
        else:
            password_form.current_password.errors.append(
                'Incorrect current password.')

    # If validation fails, re-render the main page with the errors
    return render_template('admin/account.html',
                           title='Admin Account Management',
                           password_form=password_form,
                           username_form=username_form)


# This third function HANDLES the username change
@bp.route('/admin/account/change-username', methods=['POST'])
@admin_required
def change_username():
    """Handles username change form submission."""
    # We need to instantiate both forms in case of a validation error
    username_form = ChangeUsernameForm(current_user.username)
    password_form = ChangePasswordForm()

    if username_form.validate_on_submit():
        original_username = current_user.username
        current_user.username = username_form.new_username.data
        db.session.commit()
        flash(
            f'Username successfully changed from "{original_username}" to "{current_user.username}".',
            'success')
        return redirect(url_for('main.admin_account'))

    # If validation fails, re-render the main page with the errors
    return render_template('admin/account.html',
                           title='Admin Account Management',
                           password_form=password_form,
                           username_form=username_form)


# === COOKIE CONSENT ROUTE ===
@bp.route('/set-cookie-consent', methods=['POST'])
def set_cookie_consent():
    """Sets a cookie to remember the user's consent choice."""
    consent = request.json.get('consent', 'false')
    response = make_response(jsonify(success=True))

    # Set a cookie that expires in 1 year (31536000 seconds)
    response.set_cookie('cookie_consent', consent, max_age=31536000,
                        samesite='Lax')
    return response
