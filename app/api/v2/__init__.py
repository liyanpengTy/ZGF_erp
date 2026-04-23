# 微信小程序
from flask import Blueprint
from flask_restx import Api
from app.api.v2.auth import auth_ns

bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')
api = Api(bp, doc='/docs', title='ZGF ERP 小程序端API', version='1.0')

# 导入并注册命名空间
api.add_namespace(auth_ns, path='/auth')
