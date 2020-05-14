from werkzeug.serving import run_simple
from werkzeug.wrappers import Response, Request
from werkzeug.routing import Map, Rule


class PPrika(object):
    def __init__(self):
        self.url_map = Map()
        self.view_functions = {}  # endpoint: view_func
        self.request = None
        self.url_adapter = None

    def wsgi_app(self, environ, start_response):
        self.request = Request(environ)  # 类似Flask.request
        self.url_adapter = self.url_map.bind_to_environ(environ)
        endpoint, args = self.url_adapter.match()

        rv = self.view_functions[endpoint](**args)
        headers = [('Content-type', 'text/html')]  # todo 视图函数返回值也要可设置 str/status/header
        # headers.append(("Access-Control-Allow-Origin", "*"))
        # headers.append(("Cache-Control", "no-cache"))
        # path = environ.get('PATH_INFO') or '/'
        response = Response(rv, status=200, headers=headers)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def run(self, host='localhost', port=6000, debug=False):
        run_simple(host, port, self, use_debugger=debug)

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

        # 为已有func的endpoint不带func地绑定新path?
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
