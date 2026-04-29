"""认证响应构建器"""
from app.schemas.auth.user import UserLoginSchema
from app.utils.response import ApiResponse


class LoginResponseBuilder:
    """登录响应构建器"""

    @staticmethod
    def build(user, access_token, refresh_token, factories, current_factory):
        """构建登录响应"""
        user_schema = UserLoginSchema()
        user_info = user_schema.dump(user)

        return ApiResponse.success({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_info': user_info,
            'factories': factories,
            'current_factory': current_factory
        })

    @staticmethod
    def build_admin(user, access_token, refresh_token):
        """构建管理员登录响应"""
        return LoginResponseBuilder.build(user, access_token, refresh_token, [], None)

    @staticmethod
    def build_employee(user, access_token, refresh_token, factories, current_factory):
        """构建员工登录响应"""
        return LoginResponseBuilder.build(user, access_token, refresh_token, factories, current_factory)
