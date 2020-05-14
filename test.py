from pprika import PPrika

app = PPrika()


def index():
    return '<h1>Hello world!</h1>'


@app.route('/nyan')
def meow():
    return 'meow meow meow'


@app.route('/favicon.ico', 'favicon')
def favicon():
    return '垃圾chrome拿nm的ico报错'  # todo 捕捉没有favicon而500报错


app.add_url_rule('/', 'index', index)

if __name__ == '__main__':
    app.run('localhost', 9000, debug=True)  # 垃圾chrome拒绝请求6000端口
