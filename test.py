from pprika import PPrika, request

app = PPrika()


def index():
    print(type(request), request, request.args)
    return '<h1>Hello world!</h1>'


@app.route('/nyan<int:oid>')  # werkzeug支持的动态路由
def meow(oid):
    print(oid)
    return f'meow {oid} meow'


@app.route('/favicon.ico', 'favicon')  # path, endpoint
def favicon():
    return '垃圾chrome拿nm的ico报错'  # todo 捕捉没有favicon而500报错


app.add_url_rule('/', 'index', index)

if __name__ == '__main__':
    app.run('localhost', 9000, use_debugger=True)  # 垃圾chrome拒绝请求6000端口
