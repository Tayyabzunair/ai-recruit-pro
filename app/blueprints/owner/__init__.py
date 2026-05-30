from flask import Blueprint

owner_bp = Blueprint('owner', __name__, template_folder='templates')

from app.blueprints.owner import routes, forms
