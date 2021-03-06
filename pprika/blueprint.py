class Blueprint(object):
    """
    蓝图，与app一样进行路由绑定，但url会加上前缀以示区分
    url_prefix：可以与其他蓝图/app绑定同样的
    name：需要唯一
    需要在app中调用 'register_blueprint' 将路由信息注册到app上
    """
    def __init__(self, name, url_prefix=None):
        if url_prefix is None:
            url_prefix = '/' + name
        self.name = name
        self.url_prefix = url_prefix
        self._deferred_funcs = []

    def register(self, app):
        """
        接受app的 'register_blueprint' 调用，注册本路由
        简单起见，注册时url_prefix不可再变
        """
        for f in self._deferred_funcs:  # 注册一些需要app的函数
            f(app)  # 要实现注册时更改url_prefix得加一层BlueprintState

    def add_url_rule(self, path, endpoint=None, view_func=None, **options):
        """
        与app的同名方法很像，但为path自动添上 url_prefix，endpoint添上bp_name前缀
        处理完参数将形成匿名函数推迟到app创建后、注册该blueprint时才正式注册路由
        """
        path = "/".join((self.url_prefix.rstrip("/"), path.lstrip("/")))

        if view_func and hasattr(view_func, "__name__"):
            assert (
                "." not in view_func.__name__
            ), '视图函数名不应带"."'

        if endpoint:
            assert "." not in endpoint, 'endpoint参数不可带"."'
        if endpoint is None:
            assert view_func is not None, "无endpoint时view_func不可为空"
            endpoint = view_func.__name__
        endpoint = f'{self.name}.{endpoint}'

        # 函数通过deferred_funcs转发，等到有了app再执行(注册rule)
        self._deferred_funcs.append(
            lambda a: a.add_url_rule(path, endpoint, view_func, **options)
        )

    def route(self, path, **options):
        """
        add_url_rule的装饰器版本，作用一致
        """
        def wrapper(func):
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(path, endpoint, func, **options)
            return func
        return wrapper

    def register_error_handler(self, code_or_exception, func):
        """
        注册错误处理器，仅作用于当前blueprint的请求
        """
        self._deferred_funcs.append(
            lambda a: a.register_error_handler(code_or_exception, func, self.name)
        )

    def error_handler(self, code_or_exception):
        """
        register_error_handler的装饰器版本
        """
        def wrapper(func):
            self._deferred_funcs.append(
                lambda a: a.register_error_handler(code_or_exception, func, self.name)
            )
            return func
        return wrapper

    def app_error_handler(self, code_or_exception):
        """
        注册错误处理器，作用于所有请求
        """
        def wrapper(func):
            self._deferred_funcs.append(
                lambda a: a.error_handler(code_or_exception)(func)
            )
            return func
        return wrapper
