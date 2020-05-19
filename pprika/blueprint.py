class Blueprint(object):
    """
    蓝图，与app一样进行路由绑定，但url会加上前缀以示区分
    需要在app中调用 'register_blueprint' 将路由信息注册到app上
    """
    def __init__(self, name, url_prefix=None):
        if url_prefix is None:
            url_prefix = '/' + name
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_funcs = []

    def register(self, app):
        """
        接受app的 'register_blueprint' 调用，注册本路由
        简单起见，注册时url_prefix不可再变
        """
        for f in self.deferred_funcs:  # 注册一些需要app的函数
            f(app)  # todo 要实现注册时url_prefix还是得加一层BlueprintState

    def add_url_rule(self, path, endpoint=None, view_func=None, **options):
        """
        与app的同名方法很像，但为path自动添上 url_prefix，endpoint添上bp_name前缀
        处理完参数将形成匿名函数推迟到app创建后、注册该blueprint时才正式注册路由
        """
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

    def route(self, path, **options):
        """
        add_url_rule的装饰器版本，作用一致
        """
        def wrapper(func):
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(path, endpoint, func, **options)
            return func
        return wrapper
