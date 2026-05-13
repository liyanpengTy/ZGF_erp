"""V1 API 蓝图与命名空间注册。"""

from flask import Blueprint
from flask_restx import Api

from app.api.v1.auth import NAMESPACE_ROUTES as AUTH_NAMESPACE_ROUTES
from app.api.v1.base_data import NAMESPACE_ROUTES as BASE_DATA_NAMESPACE_ROUTES
from app.api.v1.business import NAMESPACE_ROUTES as BUSINESS_NAMESPACE_ROUTES
from app.api.v1.profile import NAMESPACE_ROUTES as PROFILE_NAMESPACE_ROUTES
from app.api.v1.system import NAMESPACE_ROUTES as SYSTEM_NAMESPACE_ROUTES

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

api = Api(
    bp,
    doc='/docs',
    title='ZGF_ERP_PC_API',
    version='1.0',
    description='ZGF_ERP_PC_API 文档'
)

ALL_NAMESPACE_ROUTES = (
    AUTH_NAMESPACE_ROUTES
    + SYSTEM_NAMESPACE_ROUTES
    + PROFILE_NAMESPACE_ROUTES
    + BASE_DATA_NAMESPACE_ROUTES
    + BUSINESS_NAMESPACE_ROUTES
)

for namespace, path in ALL_NAMESPACE_ROUTES:
    api.add_namespace(namespace, path=path)
