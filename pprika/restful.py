from .blueprint import Blueprint
from functools import partial
from .context import request
from .helpers import make_response
from werkzeug.exceptions import HTTPException
from sys import exc_info
from traceback import print_exception
from werkzeug.datastructures import FileStorage
from decimal import Decimal


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

    def __init__(self, message=None, status=None):
        self.message = message or self.message
        self.status = status or self.status  # 大多数时候都是修改message的，放前面

    def get_response(self):
        body = {'message': self.message}
        rv = body, self.status
        return make_response(rv)

    def __str__(self):
        status = self.status or "???"
        msg = self.message or "Unknown Error"
        return "<%s '%s: %s'>" % (self.__class__.__name__, status, msg)

    def __repr__(self):
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
        404/405类路由错误 request.__load__ 还未执行，blueprint为None，不被认为是Api内的错误
        """
        if request.blueprint == self.name:
            return self.handle_error(e)
            # api中的错误不使用original_handler
        return original_handler(e)

    def handle_error(self, e):
        """
        若错误来自本api，则完全替代 'app.handle_exception'
        处理所有的错误，以统一的json格式响应
        但404、405这类路由错误是全局的，不会在此处理
        """
        if isinstance(e, self.exception_cls):
            pass
        elif isinstance(e, HTTPException):
            e = self.exception_cls(e.description, e.code)
        elif isinstance(e, ApiException):
            e = self.exception_cls(e.message, e.status)
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

    注意：当被路由时若无对应method的方法将导致 405 Method Not Allowed
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
        404/405等路由错误在 url_rule.match 时就发生，无需也无法在此处理
        """
        method = request.method.lower()

        func = getattr(cls, method, None)
        if func is None and method == 'head':
            func = getattr(cls, 'get', None)

        return func(cls(), *args, **kwargs)


class Namespace(dict):
    """支持以属性的方式调用的字典"""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


_friendly_location = {
    u'json': u'the JSON body',
    u'form': u'the post body',
    u'args': u'the query string',
    u'values': u'the post body or the query string',
    u'headers': u'the HTTP headers',
    u'cookies': u'the request\'s cookies',
    u'files': u'an uploaded file',
}


class Argument(object):
    """
    对某一请求参数格式要求的抽象
    调用parse方法可以获得按要求解析的值

    dest：参数解析后在Namespace里对应的键名，相当于换了个名字
    location：该参数所处位置/格式，如queryString、requestBody之类的，其中靠后的优先(多值时会覆盖前面的)
    nullable：允不允许请求中的参数值为Null(None)
    """

    def __init__(self, name, dest=None, default=None, required=False,
                 type=str, location=('json', 'values',), nullable=True):
        self.name = name
        self.dest = dest
        self.default = default
        self.required = required
        self.type = type
        self.location = (location,) if isinstance(location, str) else location
        self.nullable = nullable

    def __str__(self):
        return f"Argument 'name: {self.name}, type: {self.type}'"

    def convert(self, value):
        """按self.type尝试对传入的value进行转化"""

        if value is None:
            if not self.nullable:
                raise ValueError('该参数不可为null')
            else:
                return None
        elif isinstance(value, FileStorage) and self.type == FileStorage:
            return value

        if self.type is Decimal:
            return self.type(str(value))
        else:
            return self.type(value)

    def handle_validation_error(self, error, bundle_errors):
        """根据bundle_errors决定抛出异常或将其返回收集"""

        msg = {self.name: str(error)}
        if bundle_errors:
            return error, msg
        raise ApiException(message=msg, status=400)

    def parse(self, req, bundle_errors=False):
        """根据全局变量request解析参数，也可将自定义的request作为参数req传入"""

        values = []  # 同一个loc、多个loc都可能造成一键多值
        result = None  # 但仅返回所有合法值的最后一个，因此location中靠后的更优先

        for loc in self.location:
            value = getattr(req, loc, None)

            if callable(value):
                value = value()
            if not value:  # 该location无任何参数
                continue

            if hasattr(value, "getlist"):  # 此时value为werkzeug.datastructures.MultiDict
                value = value.getlist(self.name)  # 返回列表
            else:
                value = value.get(self.name)
                value = [value] if value else []  # value为一般dict

            req.arg_keys.discard(self.name)
            # 将处理过的参数删去，便于 parse_args 判断请求是否带有多余参数
            values.extend(value)
            # value为None说明请求中该name对应的value就是None

        for value in values:
            try:
                value = self.convert(value)
            except Exception as e:
                return self.handle_validation_error(e, bundle_errors)
            result = value or result

        if not result and self.required:  # 必需参数缺失
            locations = [_friendly_location.get(loc, loc) for loc in self.location]
            msg = f"Missing in {' or '.join(locations)}"
            return self.handle_validation_error(KeyError(msg), bundle_errors)

        if not result:  # 非必需缺失，以默认值代替
            if callable(self.default):
                return self.default(), None
            else:
                return self.default, None

        return result, None  # None表示无错误信息


class RequestParser(object):
    """
    类似于flask-restful的同名类，提供方便的参数添加与解析
    :param bundle_errors：是否等待所有error产生再统一抛出
    """

    def __init__(self, bundle_errors=True):
        self.args = []
        self.bundle_errors = bundle_errors

    @staticmethod
    def get_all_args(req):
        """
        返回 req 较有可能是参数的key，之后每parse一个就弹出
        若最后不为空则说明请求中含有多余的参数
        """

        arg_keys = set()
        for loc in ['json', 'values', 'files']:
            # request并不都是请求参数，如cookies、headers部分键值是每次请求都固定的
            value = getattr(req, loc, None)

            if not value:
                continue

            if hasattr(value, 'keys'):
                for arg in value.keys():
                    arg_keys.add(arg)
        return arg_keys

    def add_argument(self, name, **kwargs):
        """
        添加一个参数以待解析
        注意：在视图函数中add的参数对其他视图无影响，因为每次请求Resource实例都重新构造

        :param name：可以是参数名或Argument实例
        """

        if isinstance(name, Argument):
            self.args.append(name)
        else:
            self.args.append(Argument(name, **kwargs))

        return self

    def parse_args(self, req=request, strict=False, http_error_code=400):
        """
        从req中解析所有添加的参数，并以Namespace(可看作dict)返回

        :param req: 覆盖原有的全局request进行参数解析
        :param strict: 若req未提供必需的参数，则抛出 BadRequest 400 错误
        :param http_error_code：bundle_errors为True时使用的默认错误码
        """

        namespace = Namespace()
        errors = {}
        req.arg_keys = self.get_all_args(req) if strict else set()

        for arg in self.args:
            value, msg = arg.parse(req, self.bundle_errors)  # 若bundle_errors为False，异常将直接抛出

            if not isinstance(value, BaseException):
                namespace[arg.dest or arg.name] = value
            else:  # ValueError: value非法(如None)，等其他异常
                errors.update(msg)

        if errors:
            raise ApiException(message=errors, status=http_error_code)  # errors将以json响应
        if strict and req.arg_keys:
            msg = '未知参数: %s' % ', '.join(req.arg_keys)
            raise ApiException(message=msg, status=400)

        return namespace
