from json import dumps
from functools import partial
from werkzeug.wrappers import Response, BaseResponse
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException

json_config = {'ensure_ascii': False, 'indent': None, 'separators': (',', ':')}
compact_dumps = partial(dumps, **json_config)


def make_response(rv=None):
    """
    rv为视图函数返回值(body, status, headers)三元组、或响应实例
    将返回Response对象实例
    """
    status = headers = None

    if isinstance(rv, (BaseResponse, HTTPException)):
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

    if isinstance(rv, (dict, list)):
        rv = compact_dumps(rv)
        headers = Headers(headers)
        headers.setdefault('Content-type', 'application/json')
    elif rv is None:
        pass
    elif not isinstance(rv, (str, bytes, bytearray)):
        raise TypeError(f'视图函数返回的响应体类型非法: {type(rv)}')

    response = Response(rv, status=status, headers=headers)
    return response
