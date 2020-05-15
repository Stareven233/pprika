from werkzeug.serving import run_simple
from werkzeug.wrappers import Response, BaseResponse
from werkzeug.routing import Map, Rule
from .context import RequestContext, _req_ctx_ls
from werkzeug.datastructures import Headers
from json import dumps
from functools import partial

json_config = {'ensure_ascii': False, 'indent': None, 'separators': (',', ':')}
compact_dumps = partial(dumps, **json_config)


class PPrika(object):
    def __init__(self):
        self.url_map = Map()
        self.view_functions = {}  # endpoint: view_func

    def wsgi_app(self, environ, start_response):
        ctx = RequestContext(self, environ)
        try:
            ctx.bind()
            rv = self.dispatch_request()
            response = self.make_response(rv)
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

    def make_response(self, rv=None):
        status = headers = None

        if isinstance(rv, BaseResponse):
            return rv

        if isinstance(rv, tuple):
            len_rv = len(rv)
            if len_rv == 3:
                rv, status, headers = rv
            elif len_rv == 2:
                if isinstance(rv[1], (Headers, dict, tuple, list)):
                    rv, headers = rv
                else:
                    rv, status = rv
            elif len_rv == 1:
                rv = rv[0]
            else:
                raise TypeError(
                    '视图函数返回值若为tuple至少要有响应体body，'
                    '可选status与headers，如(body, status, headers)'
                )

        if isinstance(rv, dict):
            rv = compact_dumps(rv)
            headers = Headers(headers)
            headers.setdefault('Content-type', 'application/json')
        elif rv is None:
            pass
        elif not isinstance(rv, (str, bytes, bytearray)):
            raise TypeError(f'视图函数返回的响应体类型非法:{type(rv)}')

        response = Response(rv, status=status, headers=headers)
        return response
