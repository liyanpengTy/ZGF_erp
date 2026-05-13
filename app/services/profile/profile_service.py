"""个人中心服务。"""

import os
import uuid
from datetime import datetime

from sqlalchemy import func

from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.log import LoginLog, OperationLog
from app.services.base.base_service import BaseService


class ProfileService(BaseService):
    """个人中心服务。"""

    @staticmethod
    def get_user_profile(user_id):
        """获取用户个人信息。"""
        return User.query.filter_by(id=user_id, is_deleted=0).first()

    @staticmethod
    def update_profile(user, data):
        """更新用户个人资料。"""
        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'avatar' in data:
            user.avatar = data['avatar']

        user.save()
        return user

    @staticmethod
    def change_password(user, old_password, new_password, confirm_password):
        """修改当前用户密码。"""
        if not bcrypt.check_password_hash(user.password, old_password):
            return False, '旧密码错误'
        if new_password != confirm_password:
            return False, '两次输入的新密码不一致'
        if old_password == new_password:
            return False, '新密码不能与旧密码相同'

        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.save()
        return True, '密码修改成功，请重新登录'

    @staticmethod
    def upload_avatar(user, file):
        """上传头像并更新用户资料。"""
        if not file or file.filename == '':
            return None, '请选择文件'

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in allowed_extensions:
            return None, '只支持 png、jpg、jpeg、gif 格式'

        filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.{file_ext}"
        upload_dir = 'uploads/avatar'
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        avatar_url = f'/uploads/avatar/{filename}'
        user.avatar = avatar_url
        user.save()
        return {'avatar': avatar_url, 'url': avatar_url}, None

    @staticmethod
    def get_user_stats(user_id):
        """获取用户个人中心统计数据。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None

        op_count = OperationLog.query.filter_by(user_id=user_id).count()
        login_count = LoginLog.query.filter_by(user_id=user_id, status=1).count()
        today = func.date(LoginLog.create_time) == func.current_date()
        today_login = LoginLog.query.filter(
            LoginLog.user_id == user_id,
            today,
            LoginLog.status == 1
        ).first() is not None

        return {
            'user_id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'avatar': user.avatar,
            'platform_identity': user.platform_identity,
            'platform_identity_label': user.platform_identity_label,
            'subject_type': user.get_subject_type(),
            'subject_type_label': user.get_subject_type_label(),
            'create_time': user.create_time.isoformat() if user.create_time else None,
            'last_login_time': user.last_login_time.isoformat() if user.last_login_time else None,
            'statistics': {
                'total_operations': op_count,
                'total_logins': login_count,
                'today_logined': today_login
            }
        }

    @staticmethod
    def get_current_user_from_identity(identity):
        """从 JWT identity 中解析用户 ID。"""
        if isinstance(identity, dict):
            return identity.get('user_id')
        return int(identity)
