from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature
from time import time
from . import db
from pprika import request
from .exception import NotLogin
from functools import wraps


def generate_token(name, expiration=3600):
    s = Serializer('Config.SECRET_KEY', expires_in=expiration)
    return s.dumps({'name': name, 'time': time()}).decode()
    # return s.dumps({'name': name}).decode()


def verify_token(token):
    s = Serializer('Config.SECRET_KEY')
    try:
        data = s.loads(token.encode())
    except (SignatureExpired, BadSignature):
        return None
    return data['name']


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('AuthToken')
        name = verify_token(token)

        if not token or not name:
            raise NotLogin()
        db['g']['user'] = db['users'][name]
        return func(*args, **kwargs)

    return wrapper
