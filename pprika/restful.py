from .blueprint import Blueprint
from functools import partial
from .context import request
from .helpers import make_response
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import MethodNotAllowed
from sys import exc_info
from traceback import print_exception


class ApiException(Exception):
    """
    用于 'Api.handle_error'，转化所有类型的错误并返回响应

    用法：将其(或其子类)实例在视图函数中直接raise
    如：raise ApiException()

    可重写 'get_response' 并将自定义子类在初始化Api时作为参数传入，定制错误处理响应格式
    如 api = Api('api', exception_cls=CustomException)
    注意：添加的自定义属性都应当在__init__中初始化
    """

    status = None
    message = None

    def __init__(self, status=None, message=None):
        self.status = status or self.status
        self.message = message or self.message

    def get_response(self):
        body = {'message': self.message}
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
        self._deferred_funcs.append(lambda a: self._init_app(a))

    def _init_app(self, app):
        if not app.api_set:
            app.handle_exception = partial(self._error_router, app.handle_exception)
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
        但404这类路由错误是全局的，不会在此处理
        """
        if isinstance(e, self.exception_cls):
            pass
        elif isinstance(e, HTTPException):
            e = self.exception_cls(e.code, e.description)
        else:
            print_exception(*exc_info())
            e = self.exception_cls(500, repr(e))
        return e.get_response()

    def add_resource(self, resource, path, **kwargs):
        """
        将Resource的子类解析后作为路由规则加入
        用法同 flask-restful 但更简单(简陋)
        """
        endpoint = kwargs.pop('endpoint', None) or resource.__name__.lower()
        view_func = resource.as_view

        for decorator in resource.decorators:
            view_func = decorator(view_func)

        if not kwargs.get('methods'):
            kwargs['methods'] = resource.get_views()

        self.add_url_rule(path, endpoint, view_func, **kwargs)


class Resource(object):
    """
    汇集同一路由下对应不同method的视图函数

    用法：继承该类，并添加与method同名的视图函数作为其方法
    将视图函数的装饰器作为列表赋给 cls.decorators，对该Resource内所有方法都适用

    注意：当被路由时若无对应method的方法将引发 405 Method Not Allowed
    且类里除了视图函数以外不宜有其他方法，尤其是名字里带下划线 "_" 的
    该类初始化(__init__调用时)暂不支持传参
    """
    decorators = []

    @classmethod
    def get_views(cls):
        """以列表形式返回该类里所有视图函数名(即get, post等methods)"""
        return list(filter(lambda m: '_' not in m and callable(getattr(cls, m)), dir(cls)))

    @classmethod
    def as_view(cls, *args, **kwargs):
        """
        算是视图函数的代理，被调用时会将所有参数转给对应方法的真正处理函数
        """
        method = request.method.lower()

        func = getattr(cls, method, None)
        if func is None and method == 'head':
            func = getattr(cls, 'get', None)

        if func is None:
            raise MethodNotAllowed()

        return func(cls(), *args, **kwargs)
