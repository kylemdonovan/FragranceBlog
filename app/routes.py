# app/routes.py
# FINAL CORRECTED Comprehensive version with Slugs, RTE Key, and Cloudinary Image Uploads

from app import limiter
from feedgen.feed import FeedGenerator
from flask import Response, url_for
from app.forms import (LoginForm, RegistrationForm, PostForm, CommentForm, ContactForm)
# --- Core Flask & Extension Imports ---
from flask import (render_template, flash, redirect, url_for, request,
                   Blueprint, current_app)
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from urllib.parse import urlsplit
from functools import wraps
import os # Often needed for file paths or env vars directly


# --- App Specific Imports ---
from app import db
from app.models import User, Post, Comment, Tag # Ensure Post model has slug and image_url fields
# Remove FileSize import if not used directly in this file
from app.forms import (LoginForm, RegistrationForm, PostForm, CommentForm, RequestPasswordResetForm, ResetPasswordForm)

# --- Image Handling Imports ---
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
# NOTE: cloudinary.api might be needed if deleting images later, but not for upload

# --- Create Blueprint ---
bp = Blueprint('main', __name__)


# === Helper Functions ===

# --- Decorator for Admin Routes ---
def admin_required(f):
    """Ensures the user is logged in and is an admin."""
    @wraps(f)
    @login_required # Apply login_required first
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# --- Helper function to upload to Cloudinary (SINGLE CORRECT VERSION) ---
def upload_to_cloudinary(file_to_upload):
    """
    Uploads a file to Cloudinary if configured.
    Returns the secure URL on success, None on failure or if not configured.
    """
    # --- Initial Checks ---
    if not file_to_upload:
        return None
    if not current_app.config.get('CLOUDINARY_CLOUD_NAME'):
         current_app.logger("--- Upload Helper: Cloudinary not configured in Flask app. ---")
         flash("Image upload service is not configured.", "warning")
         return None # Can't upload if keys aren't set

    filename = secure_filename(file_to_upload.filename)
    if not filename:
        current_app.logger("--- Upload Helper: Invalid filename after sanitizing. ---")
        flash("Invalid image filename.", "warning")
        return None

    current_app.logger(f"--- Upload Helper: Attempting to upload '{filename}' ---")

    # --- ONE Try/Except block for the upload ---
    try:
        options = {
            'folder': "fragrance_blog", # Organize uploads in Cloudinary
            'resource_type': 'auto' # Detect if image, video, etc.
        }
        upload_result = cloudinary.uploader.upload(file_to_upload, **options)
        secure_url = upload_result.get('secure_url')
        if secure_url:
            current_app.logger(f"--- Upload Helper: Success! URL: {secure_url} ---")
            return secure_url
        else:
            current_app.logger(f"--- Upload Helper: Failed - No secure_url. Result: {upload_result} ---")
            flash("Image upload failed to return a valid URL.", "danger")
            return None
    except Exception as e:
        current_app.logger(f"--- Upload Helper: FAILED with exception: {e} ---")
        flash(f"Image upload encountered an error. Please try again later.", "danger")
        # Use Flask's logger for better error tracking in production
        current_app.logger.error(f"Cloudinary upload failed: {e}", exc_info=True)
        return None
    # --- End of single Try/Except block ---

# === End of upload_to_cloudinary function ===


# === Public Routes ===

@bp.route('/')
@bp.route('/index')
def index():
    """Displays the homepage with paginated posts."""
    page = request.args.get('page', 1, type=int)
    per_page = 5 # Number of posts per page
    query = sa.select(Post).order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    next_url = url_for('main.index', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.index', page=pagination.prev_num) if pagination.has_prev else None

    return render_template('index.html', title='Home', posts=posts,
                           next_url=next_url, prev_url=prev_url, pagination=pagination)


# === CORRECTED Post Route ===
@bp.route('/post/<string:slug>', methods=['GET', 'POST'])
def post(slug):
    """Displays a single post by its slug and handles comment submission."""
    # Query by slug instead of id
    post_obj = db.session.scalar(sa.select(Post).filter_by(slug=slug))

    # --- Corrected block for when post is NOT found ---
    if post_obj is None:
        flash(f'Post "{slug}" not found.', 'warning')
        return redirect(url_for('main.index'))
    # --- End of corrected block ---

    form = CommentForm()
    # Handle comment submission (only on valid POST requests)
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
            # Use the correct flash message for comment saving errors
            flash(f'Error saving comment: {e}', 'danger')
            current_app.logger(f"Error saving comment for post {post_obj.id}: {e}")
            current_app.logger.error(f"DB Error saving comment: {e}", exc_info=True) # Log detailed error
        # Redirect after POST to clear form and prevent resubmission
        return redirect(url_for('main.post', slug=post_obj.slug))

    # Fetch comments for display (on GET request or failed POST validation)
    page = request.args.get('page', 1, type=int)
    per_page_comments = 10
    comments_query = sa.select(Comment).where(Comment.post_id == post_obj.id).order_by(Comment.timestamp.desc())
    pagination_comments = db.paginate(comments_query, page=page, per_page=per_page_comments, error_out=False)
    comments = pagination_comments.items

    # Generate URLs for comment pagination links
    next_url = url_for('main.post', slug=slug, page=pagination_comments.next_num) if pagination_comments.has_next else None
    prev_url = url_for('main.post', slug=slug, page=pagination_comments.prev_num) if pagination_comments.has_prev else None

    # Render the template for GET requests or if comment form validation failed
    return render_template('post.html', title=post_obj.title, post=post_obj, form=form,
                           comments=comments, next_url=next_url, prev_url=prev_url, pagination_comments=pagination_comments)

# === End of post function ===


# --- <<< SEARCH ROUTE >>> ---
@bp.route('/search')
def search():
    """Handles post search queries."""
    query_param = request.args.get('q', '', type=str) # Get search term from URL arg 'q'

    if not query_param:
        # If no search term, maybe redirect to index or show a message
        # Or just show the search results page without results
        flash("Please enter a search term.", "info")
        # Optionally redirect: return redirect(url_for('main.index'))
        page = 1
        pagination = None
        posts = []
    else:
        page = request.args.get('page', 1, type=int)
        per_page = 10 # Or your preferred posts per page for search results

        # --- Perform the Search Query ---
        # Search title OR body using case-insensitive LIKE (ilike)
        search_term = f"%{query_param}%" # Add wildcards for partial matches
        query = sa.select(Post).where(
            sa.or_(
                Post.title.ilike(search_term),
                Post.body.ilike(search_term)
            )
        ).order_by(Post.timestamp.desc()) # Order results by newest first

        pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
        posts = pagination.items
        # --- End Search Query ---

    # Generate pagination URLs for search results
    # Need to include the original query param 'q' in the pagination links
    next_url = url_for('main.search', q=query_param, page=pagination.next_num) if pagination and pagination.has_next else None
    prev_url = url_for('main.search', q=query_param, page=pagination.prev_num) if pagination and pagination.has_prev else None

    return render_template('search_results.html',
                           title=f"Search Results for '{query_param}'",
                           query=query_param, # Pass query back to template
                           posts=posts,
                           next_url=next_url,
                           prev_url=prev_url,
                           pagination=pagination)
# --- <<< END SEARCH ROUTE >>> ---

# --- <<< ADD CONTACT ROUTE >>> ---
@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Displays contact form and handles submission (placeholder)."""
    form = ContactForm()
    if form.validate_on_submit():
        # --- Placeholder Action ---
        # In a real app, you'd get the data and send an email here
        # using Flask-Mail or another method.
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message = form.message.data

        current_app.logger("--- CONTACT FORM SUBMITTED ---")
        current_app.logger(f"Name: {name}")
        current_app.logger(f"Email: {email}")
        current_app.logger(f"Subject: {subject}")
        current_app.logger(f"Message: {message[:100]}...")
        # For now, just flash a success message
        flash('Your message has been received. Thank you for contacting us!', 'success')
        # -------------------------
        return redirect(url_for('main.contact')) # Redirect after POST

    # Render the contact page on GET or failed POST validation
    return render_template('contact.html', title='Contact Us', form=form)
# --- <<< END CONTACT ROUTE >>> ---


# === Authentication Routes ===

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute;100 per day")
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        # Security: Ensure next_page is internal
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        flash('Login successful!', 'success')
        return redirect(next_page)
    # Render login page on GET or failed POST validation
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required # Good practice to require login for logout route
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# --- <<< PASSWORD RESET ROUTES >>> ---

# Placeholder function for sending email (replace later with Flask-Mail)
def send_password_reset_email(user):
    token = user.get_reset_password_token()
    # When deploying, render email templates and use Flask-Mail:
    # msg = Message('Password Reset Request',
    #               sender=current_app.config['MAIL_USERNAME'], # Or actual sender email
    #               recipients=[user.email])
    # msg.body = f'''To reset your password, visit the following link:
    # {url_for('main.reset_password', token=token, _external=True)}

    # If you did not request a password reset then simply ignore this email.
    # This token will expire in 30 minutes.
    # '''
    # mail.send(msg) # Requires Flask-Mail setup

    # --- TEMPORARY!!!: Log link ---
    reset_url = url_for('main.reset_password', token=token, _external=True)
    current_app.logger("--- PASSWORD RESET ---")
    current_app.logger(f"Simulating email send to: {user.email}")
    current_app.logger(f"Reset Link: {reset_url}")
    current_app.logger("--- END PASSWORD RESET ---")
    # ----------------------------------------


@bp.route('/reset_password_request', methods=['GET', 'POST'])
@limiter.limit("3 per hour;10 per day") # Stricter for password reset requests
def reset_password_request():
    """Handles request to reset password (sends email with token)."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Don't allow logged-in users here
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).filter_by(email=form.email.data))
        if user:
            # Email exists, generate token and simulate sending email
            send_password_reset_email(user)
            flash('Instructions to reset your password have been sent to your email (check console for link).', 'info')
        else:
            # Email doesn't exist, but show same message for security
            flash('Instructions to reset your password have been sent to your email (check console for link).', 'info')
            # Or use the validation error from the form if preferred
        return redirect(url_for('main.login')) # Redirect to login after request

    return render_template('reset_password_request.html',
                           title='Reset Password Request', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset after token verification."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Shouldn't reset if logged in

    user = User.verify_reset_password_token(token)
    if not user:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('main.reset_password_request'))

    # Token is valid, show the reset form
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Set the new password and commit
        user.set_password(form.password.data)
        try:
            db.session.commit()
            flash('Your password has been successfully reset!', 'success')
            return redirect(url_for('main.login')) # Redirect to login
        except Exception as e:
             db.session.rollback()
             flash(f'Error resetting password: {e}', 'danger')
             current_app.logger.error(f"DB Error resetting password for user {user.id}: {e}", exc_info=True)

    # Render reset form on GET or failed POST validation
    return render_template('reset_password.html', title='Reset Your Password', form=form)

# --- <<< END PASSWORD RESET ROUTES >>> ---

# === User Management Routes (Admin Only) ===

@bp.route('/admin/register', methods=['GET', 'POST'])
@admin_required
def register():
    """Handles new user registration (admin only)."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.is_admin = False # Admins create non-admin users by default
        db.session.add(user)
        try:
            db.session.commit()
            flash(f'User {user.username} created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user {user.username}: {e}', 'danger')
            current_app.logger(f"Error creating user {user.username}: {e}")
            current_app.logger.error(f"DB Error creating user: {e}", exc_info=True) # Log detailed error
        return redirect(url_for('main.admin_dashboard')) # Redirect back to dashboard

    # Render registration form on GET or failed POST validation
    return render_template('register.html', title='Register New User', form=form)


# === Admin Routes ===

@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Displays the admin dashboard with posts to manage."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
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
    """Handles creation of a new blog post, including tags."""
    form = PostForm()
    if form.validate_on_submit():
        current_app.logger("--- CREATE POST: Form Validated ---")

        # Handle image upload first
        image_file = form.image.data
        image_url = None # Default to None
        if image_file:
            current_app.logger("--- CREATE POST: Image file detected, attempting upload. ---")
            image_url = upload_to_cloudinary(image_file)
            if image_url is None:
                 flash("Image upload failed, post will be created without image.", "warning")

        # Generate slug
        new_slug = Post.generate_unique_slug(form.title.data)

        # Create Post object
        post = Post(title=form.title.data,
                    body=form.body.data,
                    author=current_user,
                    slug=new_slug,
                    image_url=image_url) # Save the URL (or None)
 

        #--- Tag Zone
        tag_string = form.tags.data
        current_tags = set()
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
            # This loop iterates through the processed tag names
            for tag_name in tag_names:
                # --- This block MUST be indented inside the for loop ---
                # Skip if somehow an empty tag name remained (belt-and-suspenders)
                if not tag_name: continue
                # Check if tag exists
                tag = db.session.scalar(sa.select(Tag).filter_by(name=tag_name))
                if tag is None:
                    # Create new tag if it doesn't exist
                    tag = Tag(name=tag_name)
                    db.session.add(tag) # Add the new tag object to the session
                    current_app.logger(f"--- CREATE POST: Adding new tag '{tag_name}' ---")
                else:
                    current_app.logger(f"--- CREATE POST: Found existing tag '{tag_name}' ---")
                # Add the found or newly created Tag object to the set for this post
                current_tags.add(tag)
                # --- End of indented block ---
        # Assign the list of Tag objects to the post's relationship
        post.tags = list(current_tags)
        current_app.logger(f"--- CREATE POST: Final tags for post: {[t.name for t in post.tags]} ---")

        #--- End Tag Zone
        


        db.session.add(post)
        try:
            db.session.commit()
            current_app.logger(f"--- CREATE POST: DB Commit Successful for post '{post.title}' ---")
            flash('Your post has been created!', 'success')
            # Redirect to admin dashboard after successful creation
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger(f"--- CREATE POST: DB Commit FAILED: {e}")
            flash(f'Database error prevented post creation: {e}', 'danger')
            current_app.logger.error(f"DB Error creating post: {e}", exc_info=True) # Log detailed error
            # If commit fails, re-render the form (don't redirect)

    # Handle GET request or validation failure (including failed DB commit)
    elif request.method == 'POST': # Only log validation errors if it was a POST
        current_app.logger(f"--- CREATE POST: Form Validation FAILED. Errors: {form.errors}")

    # Pass key for GET request or failed POST validation
    return render_template('admin/create_edit_post.html',
                           title='Create New Post',
                           form=form,
                           legend='New Post',
                           tinymce_api_key=current_app.config.get('TINYMCE_API_KEY'))


@bp.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    """Handles editing of an existing blog post, including tags."""
    post = db.get_or_404(Post, post_id) # Use 404 for robustness
    form = PostForm() # Create instance for both GET and POST

    if form.validate_on_submit(): # Only runs on valid POST submission
        current_app.logger(f"--- EDIT POST ID {post_id}: Form Validated ---")

        # --- <<< START IMAGE REMOVAL/UPDATE LOGIC >>> ---
        remove_image_checked = request.form.get('remove_image') == 'on'
        image_file = form.image.data
        # Default to keeping the existing URL unless remove is checked or new image succeeds
        new_image_url_to_save = post.image_url

        if remove_image_checked:
            current_app.logger(f"--- EDIT POST ID {post_id}: Remove image checkbox checked. ---")
            # TODO Optional: Delete old image from Cloudinary here if needed
            new_image_url_to_save = None # Mark for clearing
            flash("Existing image marked for removal.", "info")
        elif image_file:
            # Only attempt upload if NOT removing and a NEW file exists
            current_app.logger(f"--- EDIT POST ID {post_id}: New image file '{secure_filename(image_file.filename)}' detected, attempting upload. ---")
            uploaded_url = upload_to_cloudinary(image_file)
            if uploaded_url:
                # If upload succeeds, mark the new URL for saving
                # TODO Optional: Delete old image from Cloudinary if needed
                current_app.logger(f"--- EDIT POST ID {post_id}: Updating image URL from '{post.image_url}' to '{uploaded_url}' ---")
                new_image_url_to_save = uploaded_url
            else:
                # If upload fails, flash warning but don't change existing URL variable yet
                flash("New image upload failed, existing image was retained.", "warning")
        # Update the post object with the final URL decided above
        post.image_url = new_image_url_to_save
        # --- <<< END IMAGE REMOVAL/UPDATE LOGIC >>> ---


        # --- <<< START TAG PROCESSING FOR EDIT (Corrected Indentation) >>> ---
        post.tags.clear() # Clear existing tags first
        tag_string = form.tags.data
        current_tags = set()
        if tag_string:
            tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
            # This loop iterates through the processed tag names
            for tag_name in tag_names:
                # --- This block IS NOW indented correctly inside the for loop ---
                if not tag_name: continue # Skip empty tags
                # Check if tag exists
                tag = db.session.scalar(sa.select(Tag).filter_by(name=tag_name))
                if tag is None:
                    # Create new tag if it doesn't exist
                    tag = Tag(name=tag_name)
                    db.session.add(tag) # Add the new tag object to the session
                    current_app.logger(f"--- EDIT POST ID {post_id}: Adding new tag '{tag_name}' ---")
                else:
                     current_app.logger(f"--- EDIT POST ID {post_id}: Found existing tag '{tag_name}' ---")
                # Add the found or newly created Tag object to the set for this post
                current_tags.add(tag)
                # --- End of indented block ---
        # Assign the list of Tag objects to the post's relationship
        post.tags = list(current_tags)
        current_app.logger(f"--- EDIT POST ID {post_id}: Final tags for post: {[t.name for t in post.tags]} ---")
        # --- <<< END TAG PROCESSING FOR EDIT >>> ---


        # --- Update text fields and slug (if title changed) ---
        original_title = post.title
        post.title = form.title.data
        post.body = form.body.data
        if post.title != original_title:
            old_slug = post.slug
            post.slug = Post.generate_unique_slug(post.title)
            current_app.logger(f"--- EDIT POST ID {post_id}: Slug regenerated from '{old_slug}' to '{post.slug}' ---")
        # ----------------------------------------------------


        # --- Commit all changes to DB ---
        try:
            db.session.commit() # Commit all changes (title, body, image_url, slug, tags)
            current_app.logger(f"--- EDIT POST ID {post_id}: DB Commit Successful ---")
            flash('Your post has been updated!', 'success')
            # Redirect AFTER commit to the updated post's view page
            return redirect(url_for('main.post', slug=post.slug))
        except Exception as e:
            db.session.rollback()
            current_app.logger(f"--- EDIT POST: DB Commit FAILED for post ID {post_id}: {e}")
            flash(f'Database error prevented post update: {e}', 'danger')
            current_app.logger.error(f"DB Error editing post {post_id}: {e}", exc_info=True) # Log detailed error
            # If commit fails, re-render the edit form with current (failed) data
            # The 'form' object still holds the data the user tried to submit
            # The 'post' object might have partial changes, but rollback reverts DB state
    # --- End of 'if form.validate_on_submit()' block ---


    # --- Handle GET request or failed POST validation ---
    elif request.method == 'POST': # Only log validation errors if it was a POST
         current_app.logger(f"--- EDIT POST ID {post_id}: Form Validation FAILED. Errors: {form.errors}")

    # --- Populate form fields ONLY on initial GET request ---
    # If it's a POST request that failed validation or DB commit,
    # the 'form' object already holds the submitted (invalid) data from the user.
    if request.method == 'GET':
        form.title.data = post.title
        form.body.data = post.body
        # Pre-populate tags field by joining existing tag names
        form.tags.data = ', '.join([tag.name for tag in post.tags])
        # NOTE: We DO NOT pre-populate the FileField (form.image.data) on GET
        current_app.logger(f"--- EDIT POST ID {post_id}: Populating form for GET request ---")

    # --- Render Template ---
    # Pass key AND post object for GET request or failed POST validation
    # The 'post' object is needed to display the current image, even on failed POST
    return render_template('admin/create_edit_post.html',
                           title='Edit Post',
                           form=form,
                           legend='Edit Post',
                           tinymce_api_key=current_app.config.get('TINYMCE_API_KEY'),
                           post=post) # Pass post object so template can show current image


@bp.route('/tag/<string:tag_name>')
def tag(tag_name):
    """Displays posts associated with a specific tag."""
    tag_obj = db.session.scalar(sa.select(Tag).filter_by(name = tag_name.lower()))
    if tag_obj is None:
        flash(f'Tag "{tag_name}" not found.', 'warning')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type = int)
    per_page = 5
    
    query = tag_obj.posts.order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page = page, per_page = per_page, error_out = False)
    posts = pagination.items
    
    next_url = url_for('main.tag', tag_name = tag_name, page = pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.tag', tag_name = tag_name, page = pagination.prev_num) if pagination.has_prev else None
    
    return render_template('tag_posts.html', tag = tag_obj, posts = posts, title = f"Posts tagged '{tag_obj.name}'", next_url = next_url, prev_url = prev_url, pagination = pagination)

@bp.route('/admin/post/<int:post_id>/delete', methods=['POST']) # Use POST for deletion safety
@admin_required
def delete_post(post_id):
    """Handles deletion of a blog post."""
    # Ensure method is POST for safety, although route decorator handles it
    if request.method == 'POST':
        post = db.get_or_404(Post, post_id)
        post_title = post.title # Get title before deleting for flash message
        try:
            # TODO Optional: Delete associated image from Cloudinary before deleting post
            # if post.image_url:
            #     try:
            #         # Need public_id logic here if deleting Cloudinary assets
            #         # cloudinary.uploader.destroy(public_id)
            #         current_app.logger(f"--- DELETE POST: Successfully deleted image from Cloudinary for post {post_id}")
            #     except Exception as img_del_e:
            #         current_app.logger(f"--- DELETE POST: Failed to delete Cloudinary image for post {post_id}: {img_del_e}")
            #         flash("Post deleted, but failed to remove associated image from storage.", "warning")

            db.session.delete(post)
            db.session.commit()
            flash(f'Post "{post_title}" has been deleted!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting post: {e}', 'danger')
            current_app.logger(f"Error deleting post {post_id}: {e}")
            current_app.logger.error(f"DB Error deleting post {post_id}: {e}", exc_info=True) # Log detailed error
    else:
        # Should not happen due to methods=['POST'] but good practice
        flash('Invalid method for deleting post.', 'warning')

    return redirect(url_for('main.admin_dashboard'))

# --- <<< ADD RSS FEED ROUTE >>> ---
@bp.route('/feed.xml') # Or '/rss.xml', '/feed/', etc.
def rss_feed():
    """Generates the RSS feed for the blog."""
    fg = FeedGenerator()

    # --- Feed Header Information ---
    # Required: id, title, author, link (href)
    fg.id(request.url_root) # Unique ID for the feed (use site root URL)
    fg.title('Fragrance Blog - Latest Posts') # Your Blog's Title
    # Use url_for with _external=True to get the full URL
    fg.link(href=url_for('main.index', _external=True), rel='alternate')
    # Optional but recommended:
    fg.subtitle('Reviews, musings, and guides on the world of scents.') # Your blog subtitle/description
    fg.language('en') # Or your blog's language
    # Add author details (replace with your info)
    fg.author({'name': 'Your Name/Blog Name', 'email': 'your-email@example.com'})
    # Link to the feed itself
    fg.link(href=url_for('main.rss_feed', _external=True), rel='self')
    # -----------------------------


    # --- Get Latest Posts for the Feed ---
    # Adjust limit as needed (e.g., latest 15-20 posts)
    latest_posts = db.session.scalars(
        sa.select(Post).order_by(Post.timestamp.desc()).limit(20)
    ).all()
    # -----------------------------------


    # --- Add Posts to the Feed ---
    for post in latest_posts:
        fe = fg.add_entry() # Create a feed entry
        fe.id(url_for('main.post', slug=post.slug, _external=True)) # Unique ID for the entry (use post URL)
        fe.title(post.title)
        fe.link(href=url_for('main.post', slug=post.slug, _external=True))
        # Use a summary or the full content (consider length)
        # Using striptags + truncate for a clean summary
        summary = post.body | striptags | truncate(300, True)
        fe.summary(summary)
        # Or use full content (potentially large feed):
        # fe.content(post.body, type='html') # Assumes post.body is safe HTML
        fe.pubDate(post.timestamp) # Use the post's timestamp
        # Add author if you want per-post author (optional)
        # fe.author({'name': post.author.username})
    # -----------------------------


    # --- Generate the Feed XML ---
    # Use rss_str() for RSS 2.0, or atom_str() for Atom
    rss_feed_xml = fg.rss_str(pretty=True) # pretty=True makes it readable
    # -----------------------------

    # --- Return the Response ---
    return Response(rss_feed_xml, mimetype='application/rss+xml')
    # Or for Atom: return Response(fg.atom_str(pretty=True), mimetype='application/atom+xml')
    # ---------------------------

# --- <<< END RSS FEED ROUTE >>> ---

# === End of routes.py ===
