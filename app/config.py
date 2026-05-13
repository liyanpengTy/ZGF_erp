"""应用配置。"""

import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build_database_uri():
    """根据环境变量构造数据库连接串。"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')

    if all([db_user, db_password, db_host, db_name]):
        password = quote_plus(db_password)
        return f'mysql+pymysql://{db_user}:{password}@{db_host}/{db_name}'

    instance_dir = os.path.join(BASE_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    sqlite_path = os.path.join(instance_dir, 'dev.sqlite3')
    return f'sqlite:///{sqlite_path}'


class BaseConfig:
    """基础配置。"""

    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))

    WECHAT_APPID = os.getenv('WECHAT_APPID')
    WECHAT_SECRET = os.getenv('WECHAT_SECRET')

    JSON_AS_ASCII = False
    JSONIFY_MIMETYPE = 'application/json;charset=utf-8'

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))

    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    CORS_SUPPORTS_CREDENTIALS = os.getenv('CORS_SUPPORTS_CREDENTIALS', '1') == '1'


class DevelopmentConfig(BaseConfig):
    """开发环境配置。"""

    DEBUG = True


class TestingConfig(BaseConfig):
    """测试环境配置。"""

    TESTING = True


class ProductionConfig(BaseConfig):
    """生产环境配置。"""

    DEBUG = False


CONFIG_MAPPING = {
    'development': DevelopmentConfig,
    'dev': DevelopmentConfig,
    'testing': TestingConfig,
    'test': TestingConfig,
    'production': ProductionConfig,
    'prod': ProductionConfig,
}


def get_config_name():
    """返回当前环境名称。"""
    app_env = os.getenv('APP_ENV') or os.getenv('FLASK_ENV') or 'development'
    return app_env.lower()


def get_config():
    """获取当前环境对应的配置类。"""
    return CONFIG_MAPPING.get(get_config_name(), DevelopmentConfig)
