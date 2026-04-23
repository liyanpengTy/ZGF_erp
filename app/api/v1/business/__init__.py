from flask import Blueprint
from app.api.v1.business.styles import style_ns
from app.api.v1.business.style_prices import style_price_ns
from app.api.v1.business.style_processes import style_process_ns
from app.api.v1.business.style_elastics import style_elastic_ns
from app.api.v1.business.style_splices import style_splice_ns

bp = Blueprint('business', __name__, url_prefix='/business')
