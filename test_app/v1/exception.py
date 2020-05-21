from pprika.restful import ApiException
from pprika import make_response


class CustomException(ApiException):
    code = None

    def __init__(self, status=None, message=None):
        super().__init__(status, message)
        if status:
            self.code = status

    def get_response(self):
        body = {'code': self.code, 'msg': self.message, 'data': ''}
        rv = body, self.status
        return make_response(rv)


class GreenLemon(CustomException):
    code = 2333
    status = 403
    message = "太绿了太绿了"
