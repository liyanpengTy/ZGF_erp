from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import bcrypt
from app.models.auth.user import User
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserSchema
from app.schemas.profile.profile import ProfileUpdateSchema, PasswordChangeSchema
from app.utils.logger import log_operation
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

profile_ns = Namespace('profile', description='个人中心')

shared = get_shared_models(profile_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

profile_update_model = profile_ns.model('ProfileUpdate', {
    'nickname': fields.String(description='昵称', example='新昵称', max_length=50),
    'phone': fields.String(description='手机号', example='13800138000', max_length=20),
    'avatar': fields.String(description='头像URL', example='/uploads/avatar/avatar.jpg')
})

password_change_model = profile_ns.model('PasswordChange', {
    'old_password': fields.String(required=True, description='旧密码', example='123456', min_length=6, max_length=20),
    'new_password': fields.String(required=True, description='新密码', example='654321', min_length=6, max_length=20),
    'confirm_password': fields.String(required=True, description='确认新密码', example='654321', min_length=6,
                                      max_length=20)
})

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

user_schema = UserSchema()
profile_update_schema = ProfileUpdateSchema()
password_change_schema = PasswordChangeSchema()


@profile_ns.route('/info')
class ProfileInfo(Resource):
    @login_required
    @profile_ns.response(200, '成功', user_info_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        user = User.query.filter_by(id=user_id, is_deleted=0).first()

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
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = profile_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'avatar' in data:
            user.avatar = data['avatar']

        user.save()

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
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = password_change_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if not bcrypt.check_password_hash(user.password, data['old_password']):
            return ApiResponse.error('旧密码错误')

        if data['new_password'] != data['confirm_password']:
            return ApiResponse.error('两次输入的新密码不一致')

        if data['old_password'] == data['new_password']:
            return ApiResponse.error('新密码不能与旧密码相同')

        user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
        user.save()

        return ApiResponse.success(message='密码修改成功，请重新登录')


@profile_ns.route('/avatar')
class UploadAvatar(Resource):
    @login_required
    @log_operation('上传头像')
    @profile_ns.response(200, '上传成功', avatar_response)
    @profile_ns.response(400, '上传失败', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def post(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not user:
            return ApiResponse.error('用户不存在')

        if 'file' not in request.files:
            return ApiResponse.error('请选择文件')

        file = request.files['file']

        if file.filename == '':
            return ApiResponse.error('请选择文件')

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower()

        if file_ext not in allowed_extensions:
            return ApiResponse.error('只支持 png、jpg、jpeg、gif 格式')

        import os
        import uuid
        from datetime import datetime

        filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.{file_ext}"

        upload_dir = 'uploads/avatar'
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        avatar_url = f'/uploads/avatar/{filename}'
        user.avatar = avatar_url
        user.save()

        return ApiResponse.success({
            'avatar': avatar_url,
            'url': avatar_url
        }, '上传成功')


@profile_ns.route('/stats')
class ProfileStats(Resource):
    @login_required
    @profile_ns.response(200, '成功', profile_stats_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not user:
            return ApiResponse.error('用户不存在')

        from app.models.system.log import OperationLog, LoginLog
        from sqlalchemy import func

        op_count = OperationLog.query.filter_by(user_id=user_id).count()
        login_count = LoginLog.query.filter_by(user_id=user_id, status=1).count()

        today = func.date(LoginLog.create_time) == func.current_date()
        today_login = LoginLog.query.filter(
            LoginLog.user_id == user_id,
            today,
            LoginLog.status == 1
        ).first() is not None

        return ApiResponse.success({
            'user_id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'avatar': user.avatar,
            'is_admin': user.is_admin,
            'create_time': user.create_time.isoformat() if user.create_time else None,
            'last_login_time': user.last_login_time.isoformat() if user.last_login_time else None,
            'statistics': {
                'total_operations': op_count,
                'total_logins': login_count,
                'today_logined': today_login
            }
        })
