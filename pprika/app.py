from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from .context import RequestContext, request
from .helpers import make_response
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError


class PPrika(object):
    """
    类似于flask的Flask，其示例用于注册路由、启动应用等
    专注于 restful，有方便灵活的错误处理，支持蓝图
    因此将不会有静态资源、模板、session、重定向等的实现
    应该会有数据库连接、请求钩子等功能...
    """
    def __init__(self):
        self.url_map = Map()
        self.view_functions = {}  # {endpoint: view_func}
        self.blueprints = {}  # {bp_name: blueprint}
        self.error_handlers = {}  # {bp_name: {status: {error: function}}}
        self.api_set = set()  # {bp_name, bp_name, ...}

    def wsgi_app(self, environ, start_response):
        """
        类似flask的同名函数 'wsgi_app'
        WSGI app，接受 __call__ / 前方server 调用，处理所有请求的入口
        匹配、处理请求并返回响应结果，捕捉、处理异常
        """
        ctx = RequestContext(self, environ)
        try:
            try:
                ctx.bind()
                rv = self.dispatch_request()
                response = make_response(rv)
            except Exception as e:
                response = self.handle_exception(e)
            return response(environ, start_response)
        finally:
            ctx.unbind()

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def run(self, host='localhost', port=6000, **options):
        """
        以 werkzeug 提供的服务器启动该应用实例
        以run_simple的 use_reloader、use_debugger 实现灵活的debug
        """
        options.setdefault("threaded", True)  # 线程隔离
        run_simple(host, port, self, **options)

    def add_url_rule(self, path, endpoint=None, view_func=None, **options):
        """
        类似于flask的同名函数 `add_url_rule`，但仅实现了最基本的功能
        将一个url rule注册到对应的endpoint上，并把endpoint关联到处理函数view_func上
        借助endpoint实现url与func多对一，其中url与endpoint一对一，endpoint与view_func一对一
        """
        if endpoint is None:
            assert view_func is not None, "无endpoint时view_func不可为空"
            endpoint = view_func.__name__

        methods = options.pop('methods', '') or ("GET",)
        if isinstance(methods, str):
            # 即允许了类似methods="POST"
            methods = (methods,)
        methods = set(item.upper() for item in methods)

        rule = Rule(path, methods=methods, endpoint=endpoint, **options)
        self.url_map.add(rule)

        # 为已有func的endpoint不带func地绑定新path - 单func多@route?
        if view_func is not None:
            old_func = self.view_functions.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError("此endpoint已有对应函数: %s" % endpoint)
            self.view_functions[endpoint] = view_func

    def route(self, path, **options):
        """
        类似于flask的同名函数 `route`
        add_url_rule的装饰器版本，作用一致
        """
        def wrapper(func):
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(path, endpoint, func, **options)
            return func
        return wrapper

    def dispatch_request(self):
        """
        接受 'wsgi_app'的调用，通过请求上下文进行url匹配，得到对应endpoint与函数参数args
        再以endpoint作为键值得到处理该url的视图函数，传入args，返回函数结果
        """
        if request.routing_exception is not None:
            return self.handle_user_exception(request.routing_exception)
        # 'url_adapter.match' 时可能产生的路由错误

        try:
            endpoint, args = request.endpoint, request.view_args
            rv = self.view_functions[endpoint](**args)
        except Exception as e:
            rv = self.handle_user_exception(e)
        return rv

    def register_blueprint(self, blueprint):
        """
        接收blueprint实例，通过其register方法实现注册
        需保证注册的blueprint名都唯一
        """
        bp_name = blueprint.name
        if bp_name in self.blueprints:
            assert blueprint is self.blueprints[bp_name], f"""
                已存在名为 {bp_name} 的blueprints：{self.blueprints[bp_name]}，
                请确保正在创建的 {blueprint} 名称唯一
            """
        else:
            self.blueprints[bp_name] = blueprint
        blueprint.register(self)

    @staticmethod
    def _get_exc_class_and_code(exc_class_or_code):
        """
        根据 status code 或 exception class 自动补出另一个
        若default_exceptions无code对应的类则报错
        """
        if isinstance(exc_class_or_code, int):
            try:
                exc_class = default_exceptions[exc_class_or_code]
            except KeyError:
                raise KeyError(f"""
                    {exc_class_or_code} 并非标准的HTTP错误码，
                    请用HTTPException构造自定义的HTTP错误
                """)
        else:
            exc_class = exc_class_or_code

        assert issubclass(exc_class, Exception)

        if issubclass(exc_class, HTTPException) and exc_class.code:
            return exc_class, exc_class.code
        else:
            return exc_class, None

    def _find_error_handler(self, e):
        """
        按照code优先、蓝图次要的顺序为寻找异常处理函数：
        蓝图 with code，全局 with code
        蓝图 without code，全局 without code
        若没有匹配的处理函数则返回None
        """
        exc_class, code = self._get_exc_class_and_code(type(e))

        for field, c in (
                (request.blueprint, code),
                (None, code),
                (request.blueprint, None),
                (None, None),
        ):
            if request.blueprint in self.api_set and not field:
                continue
            # .restful.Api 仅使用自身设置的错误处理器

            handler_map = self.error_handlers.setdefault(field, {}).get(c)

            if not handler_map:
                continue

            for cls in exc_class.__mro__:
                handler = handler_map.get(cls)
                if handler is not None:
                    return handler

    def register_error_handler(self, code_or_exception, func, field=None):
        """
        通过status code 或 Exception class注册一个错误处理函数func
        func被调用时接受该异常实例作为参数
        其中field为None时作用于全局(app)；为str时是蓝图名，仅作用于该蓝图(blueprint)
        """
        if isinstance(code_or_exception, Exception):
            raise ValueError(f"""
                不可注册异常实例: {repr(code_or_exception)}，
                只能是异常类或HTTP错误码
            """)

        exc_class, code = self._get_exc_class_and_code(code_or_exception)

        handlers = self.error_handlers.setdefault(field, {}).setdefault(code, {})
        handlers[exc_class] = func

    def error_handler(self, code_or_exception):
        """
        register_error_handler的全局装饰器版本
        """
        def wrapper(func):
            self.register_error_handler(code_or_exception, func)
            return func
        return wrapper

    def handle_user_exception(self, e):
        """
        处理所有注册过的异常，如果未注册则再抛出
        而HTTPException及其子类实例可直接作为响应返回
        """
        handler = self._find_error_handler(e)
        if handler is not None:
            return handler(e)
        raise e

    def handle_exception(self, e):
        """
        处理无对应处理函数或处理函数中再次抛出的异常
        非HTTPException将统一返回 500 ``InternalServerError`` 响应
        """
        if isinstance(e, HTTPException):
            return e

        server_error = InternalServerError()
        server_error.original_exception = e

        handler = self._find_error_handler(e) or self._find_error_handler(server_error)
        if handler is not None:
            server_error = handler(server_error)

        return make_response(server_error)
