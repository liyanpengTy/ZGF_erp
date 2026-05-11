from app.services import AuthService


def get_current_user():
    return AuthService.get_current_user()


def get_current_factory_id():
    return AuthService.get_current_factory_id()
