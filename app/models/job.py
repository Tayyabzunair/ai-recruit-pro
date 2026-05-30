"""
Job posting model.
"""
from datetime import datetime, date
from app.extensions import db


class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Info
    title = db.Column(db.String(150), nullable=False, index=True)
    company = db.Column(db.String(150))
    location = db.Column(db.String(100), index=True)
    job_type = db.Column(db.String(50))  # Full-time, Part-time, Internship, Contract
    experience_level = db.Column(db.String(50))  # Junior, Mid, Senior, Lead
    
    # Compensation
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_currency = db.Column(db.String(10), default='PKR')
    
    # Content
    description = db.Column(db.Text, nullable=False)
    responsibilities = db.Column(db.Text)
    requirements = db.Column(db.Text)
    benefits = db.Column(db.Text)
    skills = db.Column(db.Text)  # Comma-separated
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    deadline = db.Column(db.Date)
    
    # FK
    posted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    posted_by = db.relationship('User', backref='posted_jobs')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship(
        'Application', backref='job', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    @property
    def salary_range(self):
        if self.salary_min and self.salary_max:
            return f'{self.salary_currency} {self.salary_min:,} - {self.salary_max:,}'
        return 'Not specified'
    
    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]
    
    @property
    def is_expired(self):
        if not self.deadline:
            return False
        return self.deadline < date.today()
    
    @property
    def applications_count(self):
        return self.applications.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'job_type': self.job_type,
            'salary_range': self.salary_range,
            'skills': self.skills_list,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'is_active': self.is_active,
            'applications_count': self.applications_count,
        }
    
    def __repr__(self):
        return f'<Job {self.title}>'
