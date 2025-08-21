# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User, Subscriber
import sqlalchemy as sa
from app import db

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm): # Needed to create the first admin user
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # Custom validators to ensure username/email aren't already taken
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=140)])
    body = TextAreaField('Content',
            validators = [DataRequired()],
            render_kw = {'required': False})
    image = FileField('Featured Image (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!'),
        FileSize(max_size=5 * 1024 * 1024) # Example: Max 5MB size limit
    ])
    
    tags = StringField('Tags (comma-separated, optional)', validators = [Length(max=1000)])
    
    submit = SubmitField('Publish Post')

class CommentForm(FlaskForm):
    body = TextAreaField('Your Comment', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('Submit Comment')
    
# --- CONTACT FORM CLASS ---
class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=3, max=140)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')
# ---------------------------

# --- Reset Request Form ---
class RequestPasswordResetForm(FlaskForm):
    email = StringField('Your Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    # Optional: Validate that the email actually exists in the database
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            # Don't reveal *if* email exists, just give generic message
            # flash("Instructions sent if email exists.", "info") # Or do this in route
            # Raise validation error to prevent proceeding if desired
            raise ValidationError('There is no account with that email. You must register first.')

# --- ADD Reset Password Form ---
class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')

# === GENERAL CHANGE PASSWORD FORM ===
class ChangePasswordForm(FlaskForm): # Was AdminChangePasswordForm
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    new_password2 = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')]
    )
    submit = SubmitField('Change Password')

class ChangeUsernameForm(FlaskForm):
    new_username = StringField('New Username', validators=[DataRequired(), Length(min=3, max=64)])
    submit = SubmitField('Change Username')

    def __init__(self, original_username, *args, **kwargs):
        super(ChangeUsernameForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_new_username(self, new_username):
        if new_username.data.lower() == self.original_username.lower():
            raise ValidationError('New username cannot be the same as the current one.')
        if db.session.scalar(sa.select(User).where(User.username == new_username.data)):
            raise ValidationError('That username is already taken. Please choose a different one.')

# === EDIT COMMENT FORM ===
class EditCommentForm(FlaskForm):
    body = TextAreaField('Your Comment', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('Edit Comment')

# === CHANGE USERNAME FORM ===
class ChangeUsernameForm(FlaskForm):
    new_username = StringField('New Username', validators=[DataRequired(),
                                                           Length(min=3,
                                                                  max=64)])
    submit = SubmitField('Change Username')

    def __init__(self, original_username, *args, **kwargs):
        super(ChangeUsernameForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_new_username(self, new_username):
        # Check if the new username is the same as the old one
        if new_username.data.lower() == self.original_username.lower():
            # No need to check the database if the name isn't changing
            return

        # Check if the new username is already taken by someone else
        user = db.session.scalar(
            db.select(User).where(User.username == new_username.data))
        if user is not None:
            raise ValidationError(
                'That username is already taken. Please choose a different one.')

# === NEWSLETTER SUBSCRIPTION FORM ===
class SubscriptionForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Subscribe')

    def validate_email(self, email):
        # Check if the email is already subscribed
        subscriber = db.session.scalar(db.select(Subscriber).where(Subscriber.email == email.data.lower()))
        if subscriber is not None:
            raise ValidationError('This email address is already subscribed.')
