"""
Main routes - landing page, role-based redirect.
"""
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.blueprints.main import main_bp


@main_bp.route('/')
def index():
    """Landing page or redirect to dashboard."""
    if current_user.is_authenticated:
        if current_user.is_owner:
            return redirect(url_for('owner.dashboard'))
        return redirect(url_for('candidate.dashboard'))
    return render_template('main/landing.html')
