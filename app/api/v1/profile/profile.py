"""个人中心接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_user
from app.api.common.models import get_common_models
from app.models.system.reward_record import RewardRecord
from app.schemas.auth.user import UserSchema, UserUpdateSchema
from app.schemas.profile.profile import PasswordChangeSchema
from app.services import ProfileService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

profile_ns = Namespace('个人中心-profile', description='个人中心')

common = get_common_models(profile_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']

profile_update_model = profile_ns.model('ProfileUpdate', {
    'nickname': fields.String(description='昵称', example='新昵称'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'avatar': fields.String(description='头像 URL', example='/uploads/avatar/avatar.jpg')
})

password_change_model = profile_ns.model('PasswordChange', {
    'old_password': fields.String(required=True, description='旧密码', example='123456'),
    'new_password': fields.String(required=True, description='新密码', example='654321'),
    'confirm_password': fields.String(required=True, description='确认新密码', example='654321')
})

user_info_model = profile_ns.model('ProfileUserInfo', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'avatar': fields.String(description='头像地址'),
    'platform_identity': fields.String(description='平台身份'),
    'platform_identity_label': fields.String(description='平台身份名称'),
    'subject_type': fields.String(description='主体类型'),
    'subject_type_label': fields.String(description='主体类型名称'),
    'status': fields.Integer(description='状态'),
    'invite_code': fields.String(description='邀请码'),
    'invited_count': fields.Integer(description='邀请人数'),
    'is_paid': fields.Integer(description='是否已付费'),
    'create_time': fields.String(description='创建时间'),
    'last_login_time': fields.String(description='最后登录时间')
})

profile_statistics_detail_model = profile_ns.model('Statistics', {
    'total_operations': fields.Integer(description='累计操作次数'),
    'total_logins': fields.Integer(description='累计登录次数'),
    'today_logined': fields.Boolean(description='今日是否登录')
})

profile_stats_model = profile_ns.model('ProfileStats', {
    'user_id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'avatar': fields.String(description='头像地址'),
    'platform_identity': fields.String(description='平台身份'),
    'platform_identity_label': fields.String(description='平台身份名称'),
    'subject_type': fields.String(description='主体类型'),
    'subject_type_label': fields.String(description='主体类型名称'),
    'create_time': fields.String(description='创建时间'),
    'last_login_time': fields.String(description='最后登录时间'),
    'statistics': fields.Nested(profile_statistics_detail_model, description='个人统计数据')
})

avatar_response_data = profile_ns.model('AvatarResponseData', {
    'avatar': fields.String(description='头像相对路径'),
    'url': fields.String(description='头像访问地址')
})

profile_invited_user_model = profile_ns.model('InvitedUser', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'create_time': fields.String(description='创建时间')
})

invite_info_model = profile_ns.model('InviteInfo', {
    'invite_code': fields.String(description='邀请码'),
    'invited_count': fields.Integer(description='邀请人数'),
    'invited_users': fields.List(fields.Nested(profile_invited_user_model), description='邀请的用户列表')
})

invite_reward_model = profile_ns.model('InviteReward', {
    'need_count': fields.Integer(description='所需邀请人数'),
    'current_count': fields.Integer(description='当前邀请人数'),
    'progress': fields.Integer(description='进度百分比'),
    'pending_rewards': fields.Integer(description='待发放奖励数量'),
    'reward_received': fields.Boolean(description='是否已领取奖励'),
    'reward_type': fields.String(description='奖励类型')
})

user_info_response = profile_ns.clone('ProfileUserInfoResponse', base_response, {
    'data': fields.Nested(user_info_model, description='个人信息数据')
})

profile_stats_response = profile_ns.clone('ProfileStatsResponse', base_response, {
    'data': fields.Nested(profile_stats_model, description='个人统计数据')
})

avatar_response = profile_ns.clone('AvatarResponse', base_response, {
    'data': fields.Nested(avatar_response_data, description='头像上传结果数据')
})

invite_info_response = profile_ns.clone('InviteInfoResponse', base_response, {
    'data': fields.Nested(invite_info_model, description='邀请信息数据')
})

invite_reward_response = profile_ns.clone('InviteRewardResponse', base_response, {
    'data': fields.Nested(invite_reward_model, description='邀请奖励数据')
})

user_schema = UserSchema()
profile_update_schema = UserUpdateSchema()
password_change_schema = PasswordChangeSchema()


@profile_ns.route('/info')
class ProfileInfo(Resource):
    @login_required
    @profile_ns.response(200, '成功', user_info_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取个人信息。"""
        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')
        return ApiResponse.success(user_schema.dump(user))

    @login_required
    @profile_ns.expect(profile_update_model)
    @profile_ns.response(200, '更新成功', user_info_response)
    @profile_ns.response(400, '参数错误', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def patch(self):
        """更新个人信息。"""
        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = profile_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        user = ProfileService.update_profile(user, data)
        return ApiResponse.success(user_schema.dump(user), '更新成功')


@profile_ns.route('/password')
class ChangePassword(Resource):
    @login_required
    @profile_ns.expect(password_change_model)
    @profile_ns.response(200, '修改成功', base_response)
    @profile_ns.response(400, '参数错误', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def post(self):
        """修改当前用户密码。"""
        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = password_change_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

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
    @profile_ns.response(200, '上传成功', avatar_response)
    @profile_ns.response(400, '上传失败', error_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def post(self):
        """上传当前用户头像。"""
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
        """获取个人统计信息。"""
        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        stats = ProfileService.get_user_stats(user.id)
        return ApiResponse.success(stats)


@profile_ns.route('/invite-info')
class InviteInfo(Resource):
    @login_required
    @profile_ns.response(200, '成功', invite_info_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取用户邀请信息。"""
        from app.models.auth.user import User

        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        invited_users = User.query.filter_by(invited_by=user.id, is_deleted=0).order_by(User.id.desc()).all()
        return ApiResponse.success({
            'invite_code': user.invite_code,
            'invited_count': user.invited_count,
            'invited_users': [
                {
                    'id': invited_user.id,
                    'username': invited_user.username,
                    'nickname': invited_user.nickname,
                    'create_time': invited_user.create_time.isoformat() if invited_user.create_time else None
                }
                for invited_user in invited_users
            ]
        })


@profile_ns.route('/invite-reward')
class InviteReward(Resource):
    @login_required
    @profile_ns.response(200, '成功', invite_reward_response)
    @profile_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取邀请奖励进度。"""
        user = get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        pending_count = RewardRecord.query.filter_by(
            user_id=user.id,
            status='pending',
            is_deleted=0
        ).count()

        need_count = 5
        current_count = user.invited_count
        progress = min(100, int(current_count / need_count * 100))

        return ApiResponse.success({
            'need_count': need_count,
            'current_count': current_count,
            'progress': progress,
            'pending_rewards': pending_count,
            'reward_received': False,
            'reward_type': None
        })
