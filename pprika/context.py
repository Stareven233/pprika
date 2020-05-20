from werkzeug.local import LocalProxy, Local
from werkzeug.wrappers import Request as BaseRequest
from werkzeug.exceptions import HTTPException


def _get_req_object():
    try:
        ctx = _req_ctx_ls.ctx
        return getattr(ctx, 'request')
    except KeyError:
        raise RuntimeError('脱离请求上下文!')


_req_ctx_ls = Local()  # local storage 只考虑一般情况:一个请求一个ctx
request = LocalProxy(_get_req_object)


class Request(BaseRequest):
    def __init__(self, environ):
        self.endpoint = None
        self.view_args = None
        self.blueprint = None
        self.routing_exception = None
        super().__init__(environ)

    def __load__(self, res):
        self.endpoint, self.view_args = res

        if self.endpoint and "." in self.endpoint:
            self.blueprint = self.endpoint.rsplit(".", 1)[0]


class RequestContext(object):
    def __init__(self, app, environ):
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = Request(environ)

    def bind(self):
        global _req_ctx_ls
        _req_ctx_ls.ctx = self
        self.match_request()

    def unbind(self):
        _req_ctx_ls.__release_local__()

    def match_request(self):
        try:
            res = self.url_adapter.match()
            self.request.__load__(res)
        except HTTPException as e:
            self.request.routing_exception = e
