"""
时间所限，这是个只有后端的restful示例应用，
包含了基本的登录注册，以及本框架(pprika)特长的restful对get、post、delete请求的处理
它是一个需要登陆宣泄心声的树洞，无需登陆即可查看他人心声，但提供私密选项仅自己可见...
"""
from app import create_app

app = create_app()


@app.route('/')
def index():
    return {"msg": "太好了，是树洞"}, 233


if __name__ == '__main__':
    app.run('localhost', 9000, use_debugger=True)
