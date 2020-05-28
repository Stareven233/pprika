from werkzeug.local import LocalProxy, Local
from werkzeug.wrappers import Request as BaseRequest
from werkzeug.exceptions import HTTPException
from json import loads


def _get_req_object():
    try:
        ctx = _req_ctx_ls.ctx
        return getattr(ctx, 'request')
    except KeyError:
        raise RuntimeError('脱离请求上下文!')


_req_ctx_ls = Local()  # request_context_localStorage, 只考虑一般情况:一个请求一个ctx
request = LocalProxy(_get_req_object)


class Request(BaseRequest):
    def __init__(self, environ):
        self.rule = None  # werkzeug.routing.Rule对象
        self.view_args = None  # 将传给视图函数的参数
        self.blueprint = None  # 该请求所在蓝图名，为None表示在app上
        self.routing_exception = None  # 暂存路由错误
        super().__init__(environ)

    def __load__(self, res):
        """
        为request绑上blueprint、rule与函数参数，可调用rule.endpoint、rule.methods(集合来着?)
        不过request已有method属性
        """
        self.rule, self.view_args = res

        if self.rule and "." in self.rule.endpoint:
            self.blueprint = self.rule.endpoint.rsplit(".", 1)[0]

    @property
    def json(self):
        """从data解析json，若无数据则返回None"""
        if self.data and self.mimetype == 'application/json':
            return loads(self.data)


class RequestContext(object):
    def __init__(self, app, environ):
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = Request(environ)  # 即全局变量request

    def bind(self):
        """绑定请求上下文并匹配路由"""
        global _req_ctx_ls
        _req_ctx_ls.ctx = self
        self.match_request()

    def unbind(self):
        _req_ctx_ls.__release_local__()

    def match_request(self):
        """进行路由的匹配，得到url_rule与视图函数的调用参数"""
        try:
            res = self.url_adapter.match(return_rule=True)
            self.request.__load__(res)
        except HTTPException as e:
            self.request.routing_exception = e
            # 暂存错误，之后于handle_user_exception尝试处理
