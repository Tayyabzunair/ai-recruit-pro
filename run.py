"""
Application entry point.
Usage: python run.py
"""
import os
from app import create_app
from app.extensions import db

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Make objects available in flask shell."""
    from app.models.user import User
    from app.models.job import Job
    from app.models.application import Application
    return {'db': db, 'User': User, 'Job': Job, 'Application': Application}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
