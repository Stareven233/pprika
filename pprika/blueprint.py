class Blueprint(object):
    def __init__(self, name, url_prefix=None):
        if url_prefix is None:
            url_prefix = '/' + name
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_funcs = []

    def register(self, app, options):
        for f in self.deferred_funcs:  # 注册一些需要app的函数
            f(app)

    def add_url_rule(self, path, endpoint=None, view_func=None, **options):
        path = "/".join((self.url_prefix.rstrip("/"), path.lstrip("/")))

        if endpoint:
            assert "." not in endpoint, 'endpoint参数不可带"."'
        if endpoint is None:
            assert view_func is not None, "无endpoint时view_func不可为空"
            endpoint = view_func.__name__
        endpoint = f'{self.name}.{endpoint}'

        if view_func and hasattr(view_func, "__name__"):
            assert (
                "." not in view_func.__name__
            ), '视图函数名不应带"."'
        # 函数通过deferred_funcs转发，等到有了app再执行(注册rule)
        self.deferred_funcs.append(lambda a: a.add_url_rule(path, endpoint, view_func, **options))

    def route(self, path, endpoint=None):
        def wrapper(func):
            self.add_url_rule(path, endpoint, func)
            return func
        return wrapper
