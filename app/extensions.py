from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from sqlalchemy import MetaData

from app.core.exceptions import (
    BusinessException,
    DuplicateException,
    NotFoundException,
    PermissionDeniedException,
    UnauthorizedException,
    ValidationException,
)

NAMING_CONVENTION = {
    'ix': 'ix_%(table_name)s_%(column_0_name)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(column_0_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
