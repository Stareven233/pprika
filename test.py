from test_app import create_app
app = create_app()


@app.error_handler(404)
def not_found(e):
    print(e)
    return repr(e)


@app.route('/index')
@app.route('/home')
def index():
    # print(type(request), request, request.args)
    return '<h1>Hello 世界!</h1>', 233, [('Content-type', 'text/html;charset=utf-8')]


app.add_url_rule('/', 'index', index)


@app.route('/nyan/<int:oid>')  # werkzeug支持的动态路由
def meow(oid):
    print(oid)
    return {'cat': '喵喵喵', 'meow': oid}


@app.route('/fav')
@app.route('/favicon.ico')  # path, endpoint
def favicon():
    return '垃圾chrome拿nm的ico报错',   # todo 捕捉没有favicon而500报错


if __name__ == '__main__':
    app.run('localhost', 9000, use_debugger=True)  # 垃圾chrome拒绝请求6000端口
