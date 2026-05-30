"""
Owner forms - job posting, editing.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class JobForm(FlaskForm):
    title = StringField('Job Title', validators=[
        DataRequired(), Length(min=3, max=150)
    ])
    company = StringField('Company Name', validators=[
        Optional(), Length(max=150)
    ])
    location = StringField('Location', validators=[
        DataRequired(), Length(max=100)
    ])
    job_type = SelectField('Job Type', choices=[
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Contract', 'Contract'),
        ('Internship', 'Internship'),
        ('Remote', 'Remote'),
    ], validators=[DataRequired()])
    experience_level = SelectField('Experience Level', choices=[
        ('Entry', 'Entry Level (0-1 years)'),
        ('Junior', 'Junior (1-3 years)'),
        ('Mid', 'Mid Level (3-5 years)'),
        ('Senior', 'Senior (5+ years)'),
        ('Lead', 'Lead / Manager (8+ years)'),
    ], validators=[DataRequired()])
    
    salary_min = IntegerField('Min Salary', validators=[
        Optional(), NumberRange(min=0)
    ])
    salary_max = IntegerField('Max Salary', validators=[
        Optional(), NumberRange(min=0)
    ])
    salary_currency = SelectField('Currency', choices=[
        ('PKR', 'PKR'), ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'),
    ], default='PKR')
    
    description = TextAreaField('Job Description', validators=[
        DataRequired(), Length(min=20)
    ])
    responsibilities = TextAreaField('Key Responsibilities', validators=[Optional()])
    requirements = TextAreaField('Requirements', validators=[Optional()])
    benefits = TextAreaField('Benefits & Perks', validators=[Optional()])
    skills = StringField('Required Skills (comma-separated)', validators=[
        DataRequired(), Length(min=2)
    ])
    
    deadline = DateField('Application Deadline', validators=[Optional()])
    submit = SubmitField('Post Job')
