import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build_database_uri():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')

    if all([db_user, db_password, db_host, db_name]):
        password = quote_plus(db_password)
        return f"mysql+pymysql://{db_user}:{password}@{db_host}/{db_name}"

    instance_dir = os.path.join(BASE_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    sqlite_path = os.path.join(instance_dir, 'dev.sqlite3')
    return f"sqlite:///{sqlite_path}"


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # ========== JWT 配置（添加这部分） ==========
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))

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
