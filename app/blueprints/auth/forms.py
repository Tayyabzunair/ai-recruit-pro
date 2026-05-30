"""
Authentication forms with WTForms validation.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign In')


class SignupForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('I am a', choices=[
        ('Candidate', 'Job Seeker (Candidate)'),
        ('Owner', 'Recruiter / Employer (Owner)')
    ], validators=[DataRequired()])
    submit = SubmitField('Create Account')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower().strip()).first()
        if user:
            raise ValidationError('This email is already registered. Please login.')
