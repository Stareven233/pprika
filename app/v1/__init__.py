from pprika import Api
from ..exception import CustomException

v1 = Api('v1', url_prefix='/v1', exception_cls=CustomException)


def response(data):
    return {'code': 0, 'msg': '', 'data': data}


from . import user, voice
