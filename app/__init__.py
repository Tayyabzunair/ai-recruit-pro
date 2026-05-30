"""
Application factory.
"""
import os
from flask import Flask
from loguru import logger

from app.config import config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, mail


def create_app(config_name='development'):
    """Create and configure Flask app."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHROMA_PERSIST_DIR'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # User loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.owner import owner_bp
    from app.blueprints.candidate import candidate_bp
    from app.blueprints.chatbot import chatbot_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(owner_bp, url_prefix='/owner')
    app.register_blueprint(candidate_bp, url_prefix='/candidate')
    app.register_blueprint(chatbot_bp, url_prefix='/chat')

    # Template context processors
    register_context_processors(app)

    # Error handlers
    register_error_handlers(app)

    # Logging
    logger.add('logs/app.log', rotation='10 MB', retention='30 days', level='INFO')
    logger.info(f'App created with config: {config_name}')

    return app


def register_context_processors(app):
    """Inject global variables into all templates."""
    from datetime import datetime

    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.utcnow().year,
            'app_name': 'AI Recruit Pro',
        }


def register_error_handlers(app):
    """Register error handler pages."""
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, request
        flash('File too large! Maximum size is 10MB.', 'danger')
        return redirect(request.referrer or '/')
