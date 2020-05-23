from pprika import PPrika

db = {'voices': [], 'users': {}, 'g': {}}
# todo 换个真正的数据库
# todo 如reqparse般方便的参数验证


def create_app():
    app = PPrika()
    from .v1 import v1
    app.register_blueprint(v1)
    return app
