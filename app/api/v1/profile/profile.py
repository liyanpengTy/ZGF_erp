"""个人中心接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import get_jwt_identity
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserSchema
from app.schemas.profile.profile import ProfileUpdateSchema, PasswordChangeSchema
from app.utils.logger import log_operation
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import ProfileService, AuthService

profile_ns = Namespace('profile', description='个人中心')

shared = get_shared_models(profile_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求模型 ==========
profile_update_model = profile_ns.model('ProfileUpdate', {
    'nickname': fields.String(description='昵称', example='新昵称'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'avatar': fields.String(description='头像URL', example='/uploads/avatar/avatar.jpg')
})

password_change_model = profile_ns.model('PasswordChange', {
    'old_password': fields.String(required=True, description='旧密码', example='123456'),
    'new_password': fields.String(required=True, description='新密码', example='654321'),
    'confirm_password': fields.String(required=True, description='确认新密码', example='654321')
})

# ========== 响应模型 ==========
user_info_model = profile_ns.model('UserInfo', {
    'id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'avatar': fields.String(),
    'is_admin': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'last_login_time': fields.String()
})

profile_stats_model = profile_ns.model('ProfileStats', {
    'user_id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'avatar': fields.String(),
    'is_admin': fields.Integer(),
    'create_time': fields.String(),
    'last_login_time': fields.String(),
    'statistics': fields.Nested(profile_ns.model('Statistics', {
        'total_operations': fields.Integer(),
        'total_logins': fields.Integer(),
        'today_logined': fields.Boolean()
    }))
})

avatar_response_data = profile_ns.model('AvatarResponseData', {
    'avatar': fields.String(),
    'url': fields.String()
})

user_info_response = profile_ns.clone('UserInfoResponse', base_response, {
    'data': fields.Nested(user_info_model)
})

profile_stats_response = profile_ns.clone('ProfileStatsResponse', base_response, {
    'data': fields.Nested(profile_stats_model)
})

avatar_response = profile_ns.clone('AvatarResponse', base_response, {
    'data': fields.Nested(avatar_response_data)
})

# ========== Schema 初始化 ==========
user_schema = UserSchema()
profile_update_schema = ProfileUpdateSchema()
password_change_schema = PasswordChangeSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@profile_ns.route('/info')
class ProfileInfo(Resource):
    @login_required
    @profile_ns.response(200, '成功', user_info_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取个人信息"""
        user = get_current_user()

        if not user:
            return ApiResponse.error('用户不存在')

        return ApiResponse.success(user_schema.dump(user))

    @login_required
    @log_operation('修改个人信息')
    @profile_ns.expect(profile_update_model)
    @profile_ns.response(200, '更新成功', user_info_response)
    @profile_ns.response(400, '参数错误', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def put(self):
        """更新个人信息"""
        user = get_current_user()

        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = profile_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        user = ProfileService.update_profile(user, data)

        return ApiResponse.success(user_schema.dump(user), '更新成功')


@profile_ns.route('/password')
class ChangePassword(Resource):
    @login_required
    @log_operation('修改密码')
    @profile_ns.expect(password_change_model)
    @profile_ns.response(200, '修改成功', base_response)
    @profile_ns.response(400, '参数错误', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def put(self):
        """修改密码"""
        user = get_current_user()

        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = password_change_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        success, message = ProfileService.change_password(
            user,
            data['old_password'],
            data['new_password'],
            data['confirm_password']
        )

        if not success:
            return ApiResponse.error(message, 400)

        return ApiResponse.success(message=message)


@profile_ns.route('/avatar')
class UploadAvatar(Resource):
    @login_required
    @log_operation('上传头像')
    @profile_ns.response(200, '上传成功', avatar_response)
    @profile_ns.response(400, '上传失败', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def post(self):
        """上传头像"""
        user = get_current_user()

        if not user:
            return ApiResponse.error('用户不存在')

        if 'file' not in request.files:
            return ApiResponse.error('请选择文件')

        file = request.files['file']

        result, error = ProfileService.upload_avatar(user, file)

        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(result, '上传成功')


@profile_ns.route('/stats')
class ProfileStats(Resource):
    @login_required
    @profile_ns.response(200, '成功', profile_stats_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """个人统计"""
        user = get_current_user()

        if not user:
            return ApiResponse.error('用户不存在')

        stats = ProfileService.get_user_stats(user.id)

        if not stats:
            return ApiResponse.error('用户不存在')

        return ApiResponse.success(stats)
