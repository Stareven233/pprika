from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from .context import RequestContext, _req_ctx_ls
from .helpers import make_response


class PPrika(object):
    def __init__(self):
        self.url_map = Map()
        self.view_functions = {}  # endpoint: view_func
        self.blueprints = {}  # bp_name: blueprint

    def wsgi_app(self, environ, start_response):
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
        options.setdefault("threaded", True)  # 线程隔离
        run_simple(host, port, self, **options)

    def add_url_rule(self, path, endpoint=None, view_func=None, **options):
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

    def route(self, path, endpoint=None):
        def wrapper(func):
            self.add_url_rule(path, endpoint, func)
            return func
        return wrapper

    def dispatch_request(self):
        endpoint, args = _req_ctx_ls.ctx.url_adapter.match()
        return self.view_functions[endpoint](**args)

    def register_blueprint(self, blueprint, **options):
        bp_name = blueprint.name
        if bp_name in self.blueprints:
            assert blueprint is self.blueprints[bp_name], f"""
                已存在名为 {bp_name} 的blueprints：{self.blueprints[bp_name]}，
                请确保正在创建的 {blueprint} 名称唯一
            """
        else:
            self.blueprints[bp_name] = blueprint
        blueprint.register(self, options)
