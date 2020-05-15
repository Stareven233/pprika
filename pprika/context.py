from werkzeug.local import LocalProxy, Local
from werkzeug.wrappers import Request


def _get_req_object():
    try:
        ctx = _req_ctx_ls.ctx
        return getattr(ctx, 'request')
    except KeyError:
        raise RuntimeError('脱离请求上下文!')


_req_ctx_ls = Local()  # local storage 只考虑一般情况:一个请求一个ctx
request = LocalProxy(_get_req_object)


class RequestContext(object):
    def __init__(self, app, environ):
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = Request(environ)

    def bind(self):
        global _req_ctx_ls
        _req_ctx_ls.ctx = self

    def unbind(self):
        _req_ctx_ls.__release_local__()
