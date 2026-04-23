from flask import Blueprint
from app.api.v1.base_data.sizes import size_ns
from app.api.v1.base_data.categories import category_ns
from app.api.v1.base_data.colors import color_ns

bp = Blueprint('base_data', __name__, url_prefix='/base_data')
