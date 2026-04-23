import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # 微信配置
    WECHAT_APPID = os.getenv('WECHAT_APPID')
    WECHAT_SECRET = os.getenv('WECHAT_SECRET')
    # JSON 配置
    JSON_AS_ASCII = False
    JSONIFY_MIMETYPE = 'application/json;charset=utf-8'

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')  # 日志文件路径
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))


def get_config():
    """获取配置对象"""
    return Config()
