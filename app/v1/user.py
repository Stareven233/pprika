from . import v1, response
from pprika import request
from ..exception import LackOfInfo
from ..exception import UserAlreadyExist
from ..exception import NotFound
from ..exception import PwdError
from .. import db
from ..auth import generate_token
from pprika import Resource


class Register(Resource):
    def post(self):
        data = request.json
        name, pwd = data.get('name'), data.get('password')

        if not name or not pwd:
            raise LackOfInfo()
        if name in db['users']:
            raise UserAlreadyExist()

        data['uid'] = len(db['users']) + 1
        db['users'][name] = data

        return response(data)


class Login(Resource):
    def get(self):
        data = request.headers
        name, pwd = data.get('name'), data.get('password')

        if not name or not pwd:
            raise LackOfInfo()

        if name not in db['users']:
            raise NotFound(message='不存在该用户，请先注册')

        if pwd != db['users'][name]['password']:
            raise PwdError()

        token = generate_token(name)
        return response(token)


v1.add_resource(Register, '/users/register')
v1.add_resource(Login, '/users/token')
