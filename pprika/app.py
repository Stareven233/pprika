from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from .context import RequestContext, _req_ctx_ls
from .helpers import make_response


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

    def wsgi_app(self, environ, start_response):
        """
        类似flask的同名函数 'wsgi_app'
        WSGI app，接受 __call__ / 前方server 调用，处理所有请求的入口
        匹配、处理请求并返回响应结果，捕捉、处理异常
        """
        ctx = RequestContext(self, environ)
        try:
            ctx.bind()
            rv = self.dispatch_request()
            response = make_response(rv)
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
        endpoint, args = _req_ctx_ls.ctx.url_adapter.match()
        return self.view_functions[endpoint](**args)

    def register_blueprint(self, blueprint, **options):
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
        blueprint.register(self, options)

    def register_error_handler(self, bp_name, code_or_exception, func):
        pass
