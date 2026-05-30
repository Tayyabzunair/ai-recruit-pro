"""
Authentication routes.
"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from loguru import logger

from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm, SignupForm
from app.extensions import db
from app.models.user import User


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_owner:
            return redirect(url_for('owner.dashboard'))
        return redirect(url_for('candidate.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f'User logged in: {user.email}')
            flash(f'Welcome back, {user.name}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Role-based redirect
            if user.is_owner:
                return redirect(url_for('owner.dashboard'))
            return redirect(url_for('candidate.dashboard'))
        
        flash('Invalid email or password.', 'danger')
        logger.warning(f'Failed login attempt: {email}')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f'New user registered: {user.email} ({user.role})')
        try:
            from app.services.email_service import EmailService
            EmailService.send_welcome(user)
        except Exception as e:
            logger.error(f'Welcome email failed: {e}')
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logger.info(f'User logged out: {current_user.email}')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
