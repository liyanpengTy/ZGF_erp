from flask_restx import Namespace, Resource, fields
from flask import request, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import requests
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserLoginSchema
from datetime import datetime
import random
import string

auth_ns = Namespace('auth', description='小程序认证管理')

# 初始化 Schema
user_login_schema = UserLoginSchema()

# 请求模型
wx_login_model = auth_ns.model('WxLogin', {
    'code': fields.String(required=True, description='微信登录code')
})


@auth_ns.route('/wxlogin')
class WxLogin(Resource):
    @auth_ns.expect(wx_login_model)
    def post(self):
        """小程序微信登录"""
        data = request.get_json()
        code = data.get('code')

        # 调用微信接口获取openid
        appid = current_app.config.get('WECHAT_APPID')
        secret = current_app.config.get('WECHAT_SECRET')

        url = f'https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code'

        try:
            response = requests.get(url, timeout=10)
            wx_data = response.json()
        except Exception as e:
            return ApiResponse.error('微信登录失败')

        if 'errcode' in wx_data and wx_data['errcode'] != 0:
            return ApiResponse.error(wx_data.get('errmsg', '微信登录失败'))

        openid = wx_data.get('openid')

        if not openid:
            return ApiResponse.error('获取openid失败')

        # 查询或创建用户
        user = User.query.filter_by(openid=openid).first()

        if not user:
            # 自动注册新用户
            username = f"wx_{openid[:16]}"
            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

            user = User(
                username=username,
                password=bcrypt.generate_password_hash(random_password).decode('utf-8'),
                openid=openid,
                user_type=4,
                nickname=f"微信用户_{openid[:8]}",
                status=1
            )
            db.session.add(user)
            db.session.commit()

        # 更新最后登录时间
        user.last_login_time = datetime.now()
        db.session.commit()

        # 生成token
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        # 使用 Schema 序列化用户信息
        user_info = user_login_schema.dump(user)

        return ApiResponse.success({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_info': user_info
        })


@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """刷新token"""
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=user_id)
        return ApiResponse.success({'access_token': access_token})


@auth_ns.route('/userinfo')
class UserInfo(Resource):
    @jwt_required()
    def get(self):
        """获取当前用户信息"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return ApiResponse.error('用户不存在')

        # 使用 Schema 序列化用户信息
        user_info = user_login_schema.dump(user)

        return ApiResponse.success(user_info)