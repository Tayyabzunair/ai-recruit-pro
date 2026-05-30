"""
File and input validators.
"""
import os
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def safe_filename(filename, user_id):
    """Generate safe, unique filename."""
    from datetime import datetime
    name = secure_filename(filename)
    if not name:
        name = 'resume.pdf'
    
    # Add user_id and timestamp for uniqueness
    base, ext = os.path.splitext(name)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    return f'user{user_id}_{timestamp}_{base[:30]}{ext}'


def validate_file_size(file, max_mb=10):
    """Check file size."""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= max_mb * 1024 * 1024
