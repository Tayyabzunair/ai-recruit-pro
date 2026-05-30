"""
Application model - candidate's application to a job.
"""
from datetime import datetime
from app.extensions import db


class ApplicationStatus:
    PENDING = 'Pending'
    REVIEWED = 'Reviewed'
    SHORTLISTED = 'Shortlisted'
    INTERVIEW = 'Interview'
    HIRED = 'Hired'
    REJECTED = 'Rejected'
    
    ALL = [PENDING, REVIEWED, SHORTLISTED, INTERVIEW, HIRED, REJECTED]


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # FKs
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    
    # Extracted from resume
    full_name = db.Column(db.String(150))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    skills = db.Column(db.Text)
    experience_years = db.Column(db.Float)
    education = db.Column(db.Text)
    
    # Raw resume text (for RAG indexing)
    resume_text = db.Column(db.Text)
    resume_filename = db.Column(db.String(255))
    
    # AI Scoring
    match_score = db.Column(db.Float, default=0.0)  # 0-100
    ai_summary = db.Column(db.Text)  # AI-generated summary
    
    # Workflow
    status = db.Column(db.String(30), default=ApplicationStatus.PENDING, index=True)
    notes = db.Column(db.Text)  # Owner's private notes
    
    # RAG indexing flag
    is_indexed = db.Column(db.Boolean, default=False)
    
    # Timestamps
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint - one application per user per job
    __table_args__ = (
        db.UniqueConstraint('user_id', 'job_id', name='unique_user_job_application'),
    )
    
    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]
    
    @property
    def score_color(self):
        """Return Tailwind color class based on score."""
        if self.match_score >= 80:
            return 'green'
        elif self.match_score >= 60:
            return 'amber'
        elif self.match_score >= 40:
            return 'orange'
        return 'red'
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'skills': self.skills_list,
            'match_score': self.match_score,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'job_title': self.job.title if self.job else None,
        }
    
    def __repr__(self):
        return f'<Application {self.full_name} → {self.job.title if self.job else "?"}>'
