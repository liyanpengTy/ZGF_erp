"""个人中心服务"""
import os
import uuid
from datetime import datetime
from flask import request
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.log import OperationLog, LoginLog
from app.services.base.base_service import BaseService
from sqlalchemy import func


class ProfileService(BaseService):
    """个人中心服务"""

    @staticmethod
    def get_user_profile(user_id):
        """获取用户个人信息"""
        return User.query.filter_by(id=user_id, is_deleted=0).first()

    @staticmethod
    def update_profile(user, data):
        """更新个人信息"""
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
        """修改密码"""
        # 验证旧密码
        if not bcrypt.check_password_hash(user.password, old_password):
            return False, '旧密码错误'

        # 验证新密码和确认密码是否一致
        if new_password != confirm_password:
            return False, '两次输入的新密码不一致'

        # 验证新旧密码不能相同
        if old_password == new_password:
            return False, '新密码不能与旧密码相同'

        # 更新密码
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.save()

        return True, '密码修改成功，请重新登录'

    @staticmethod
    def upload_avatar(user, file):
        """上传头像"""
        if not file:
            return None, '请选择文件'

        if file.filename == '':
            return None, '请选择文件'

        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower()

        if file_ext not in allowed_extensions:
            return None, '只支持 png、jpg、jpeg、gif 格式'

        # 生成文件名
        filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.{file_ext}"

        # 确保目录存在
        upload_dir = 'uploads/avatar'
        os.makedirs(upload_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        avatar_url = f'/uploads/avatar/{filename}'
        user.avatar = avatar_url
        user.save()

        return {'avatar': avatar_url, 'url': avatar_url}, None

    @staticmethod
    def get_user_stats(user_id):
        """获取用户统计数据"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None

        # 操作统计
        op_count = OperationLog.query.filter_by(user_id=user_id).count()

        # 登录统计
        login_count = LoginLog.query.filter_by(user_id=user_id, status=1).count()

        # 今日是否登录
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
            'is_admin': user.is_admin,
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
        """从 JWT identity 中获取用户ID"""
        if isinstance(identity, dict):
            user_id = identity.get('user_id')
        else:
            user_id = int(identity)
        return user_id
