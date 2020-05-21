from .blueprint import Blueprint
from functools import partial
from .context import request
from .helpers import make_response
from werkzeug.exceptions import HTTPException


class ApiException(Exception):
    """
    用于 'Api.handle_error'，转化所有类型的错误并返回响应

    用法：将其(或其子类)实例在视图函数中直接raise
    如：raise ApiException()

    可重写 'get_response' 并将自定义子类在初始化Api时作为参数传入，定制错误处理响应格式
    如 api = Api('api', exception_cls=CustomException)
    注意：响应中需要的自定义属性应当在__init__中初始化
    """

    status = None
    message = None

    def __init__(self, status=None, message=None):
        if status and message:
            self.status = status
            self.message = message

    def get_response(self):
        body = {'msg': self.message}
        rv = body, self.status
        return make_response(rv)

    def __str__(self):
        status = self.status or "???"
        msg = self.message or "Unknown Error"
        return "<%s '%s: %s'>" % (self.__class__.__name__, status, msg)


class Api(Blueprint):
    """
    与flask-restful不同，Api作为Blueprint子类直接绑定于app
    与Blueprint差别：Api不使用全局错误处理器，且错误默认以json响应
    """

    exception_cls = ApiException

    def __init__(self, name, url_prefix=None, exception_cls=None):
        super().__init__(name, url_prefix)
        if exception_cls is not None:
            self.exception_cls = exception_cls
        self.deferred_funcs.append(lambda a: self._init_app(a))

    def _init_app(self, app):
        if not app.api_set:
            app.handle_user_exception = partial(self._error_router, app.handle_exception)
            # 若自身未设置对应错误处理器，则错误由handle_user_exception中再抛出
        app.api_set.add(self.name)

    def _error_router(self, original_handler, e):
        """
        若错误来自api内部，则以自带处理器处理
        否则交由源(app)处理器处理
        通过重写(override)该方法可扩大handle_error处理范围
        """
        if request.blueprint == self.name:
            return self.handle_error(e)
            # api中的错误不使用original_handler
        return original_handler(e)

    def handle_error(self, e):
        """
        若错误来自本api，则完全替代 'app.handle_exception'
        处理所有的错误，以统一的json格式响应
        """
        if isinstance(e, self.exception_cls):
            pass
        elif isinstance(e, HTTPException):
            e = self.exception_cls(e.code, e.description)
        else:
            e = self.exception_cls(500, str(e))
        return e.get_response()
