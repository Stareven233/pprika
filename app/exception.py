from pprika.restful import ApiException
from pprika import make_response


class CustomException(ApiException):
    code = None

    def __init__(self, message=None, status=None):
        super().__init__(message, status)
        self.code = self.code or status

    def get_response(self):
        body = {'code': self.code, 'msg': self.message}
        rv = body, self.status
        return make_response(rv)


class ForbiddenWord(CustomException):
    code = 2001
    status = 403
    message = "发表的文段中包含敏感词汇"


class NotFound(CustomException):
    code = 2002
    status = 404
    message = "未发现所请求的资源"


class PrivateVoice(CustomException):
    code = 2003
    status = 403
    message = "该voice设置了隐私，无法查看"


class LackOfInfo(CustomException):
    code = 1001
    status = 400
    message = "用户名或密码缺失"


class UserAlreadyExist(CustomException):
    code = 1002
    status = 401
    message = "该用户名已被注册"


class PwdError(CustomException):
    code = 1003
    status = 401
    message = "密码错误"


class NotLogin(CustomException):
    code = 1004
    status = 401
    message = "未登录或登录信息错误"
