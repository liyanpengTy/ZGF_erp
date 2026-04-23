from flask import Blueprint
from app.api.v1.profile.profile import profile_ns

bp = Blueprint('profile', __name__, url_prefix='/profile')
