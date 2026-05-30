"""
Custom decorators for route protection.
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def owner_required(f):
    """Restrict route to Owner role only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login first.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_owner:
            flash('Access denied. Owner privileges required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated


def candidate_required(f):
    """Restrict route to Candidate role only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login first.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_candidate:
            flash('Access denied. Candidate account required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated
