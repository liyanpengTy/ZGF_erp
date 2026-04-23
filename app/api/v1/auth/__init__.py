from flask import Blueprint
from app.api.v1.auth.auth import auth_ns

bp = Blueprint('auth', __name__, url_prefix='/auth')
