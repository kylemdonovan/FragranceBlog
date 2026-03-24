# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User, Subscriber
import sqlalchemy as sa
from app import db
from flask_wtf.recaptcha import RecaptchaField
from better_profanity import profanity

# Initialize the default wordlist (includes l33t speak variations)
profanity.load_censor_words()

class CommentForm(FlaskForm):
    body = TextAreaField('Your Comment', validators=[DataRequired(), Length(min=1, max=500)])
    honeypot = StringField('Leave this empty')
    submit_comment = SubmitField('Submit Comment')

class ReplyForm(FlaskForm):
    body = TextAreaField('Your Reply', validators=[DataRequired(), Length(min=1, max=500)])
    parent_id = HiddenField('Parent ID', validators=[DataRequired()])
    honeypot = StringField('Leave this empty')
    submit_reply = SubmitField('Submit Reply')

def contains_profanity(text):
    """Checks string against the better_profanity library."""
    return profanity.contains_profanity(text)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    recaptcha = RecaptchaField()
    submit = SubmitField('Register')

    def validate_username(self, username):
        if contains_profanity(username.data):
            raise ValidationError('Please choose a more appropriate username.')
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=140)])
    body = TextAreaField('Content', validators=[DataRequired()], render_kw={'required': False})
    image = FileField('Featured Image (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!'),
        FileSize(max_size=5 * 1024 * 1024)
    ])
    tags = StringField('Tags (comma-separated, optional)', validators=[Length(max=1000)])
    status = BooleanField('Publish this post immediately', default='checked')
    submit = SubmitField('Publish Post')

class CommentForm(FlaskForm):
    body = TextAreaField('Your Comment', validators=[DataRequired(), Length(min=1, max=500)])
    submit_comment = SubmitField('Submit Comment')

class ReplyForm(FlaskForm):
    body = TextAreaField('Your Reply', validators=[DataRequired(), Length(min=1, max=500)])
    parent_id = HiddenField('Parent ID', validators=[DataRequired()])
    submit_reply = SubmitField('Submit Reply')

class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=3, max=140)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')

class RequestPasswordResetForm(FlaskForm):
    email = StringField('Your Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    new_password2 = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')]
    )
    submit = SubmitField('Change Password')

class EditCommentForm(FlaskForm):
    body = TextAreaField('Your Comment', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('Edit Comment')

class ChangeUsernameForm(FlaskForm):
    new_username = StringField('New Username', validators=[DataRequired(), Length(min=3, max=64)])
    submit = SubmitField('Change Username')

    def __init__(self, original_username, *args, **kwargs):
        super(ChangeUsernameForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_new_username(self, new_username):
        if contains_profanity(new_username.data):
            raise ValidationError('Please choose a more appropriate username.')
        if new_username.data.lower() == self.original_username.lower():
            return
        user = db.session.scalar(sa.select(User).where(User.username == new_username.data))
        if user is not None:
            raise ValidationError('That username is already taken. Please choose a different one.')

class DeleteAccountForm(FlaskForm):
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit_delete = SubmitField('Delete My Account')

class SubscriptionForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Subscribe')

    def validate_email(self, email):
        subscriber = db.session.scalar(sa.select(Subscriber).where(Subscriber.email == email.data.lower()))
        if subscriber is not None:
            raise ValidationError('This email address is already subscribed.')

