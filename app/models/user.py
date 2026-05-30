"""
User model with secure password handling.
"""
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, bcrypt


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'Owner' or 'Candidate'
    
    # Profile fields
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    applications = db.relationship(
        'Application', backref='candidate', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def set_password(self, password):
        """Hash and store password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verify password."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @property
    def is_owner(self):
        return self.role == 'Owner'
    
    @property
    def is_candidate(self):
        return self.role == 'Candidate'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
