from . import v1, response
from ..exception import LackOfInfo
from ..exception import UserAlreadyExist
from ..exception import NotFound
from ..exception import PwdError
from .. import db
from ..auth import generate_token
from pprika import Resource
from pprika import RequestParser


reqparse = RequestParser()
reqparse.add_argument('name', type=str, required=True, location=['json', 'headers'])
reqparse.add_argument('password', dest='pwd', type=str, required=True, location=['json', 'headers'])


class Register(Resource):
    def __init__(self):
        self.reqparse = reqparse

    def post(self):
        args = self.reqparse.parse_args(strict=True)

        if not args.name or not args.pwd:
            raise LackOfInfo()
        if args.name in db['users']:
            raise UserAlreadyExist()

        args.uid = len(db['users']) + 1
        args.password = args.pop('pwd')
        db['users'][args.name] = args

        return response(args)


class Login(Resource):
    def __init__(self):
        self.reqparse = reqparse

    def get(self):
        args = self.reqparse.parse_args(strict=True)

        if not args.name or not args.pwd:
            raise LackOfInfo()

        if args.name not in db['users']:
            raise NotFound(message='不存在该用户，请先注册')

        if args.pwd != db['users'][args.name]['password']:
            raise PwdError()

        token = generate_token(args.name)
        return response(token)


v1.add_resource(Register, '/users/register')
v1.add_resource(Login, '/users/token')
