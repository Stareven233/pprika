from pprika import PPrika


def create_app():
    app = PPrika()
    from .main import main
    app.register_blueprint(main)
    from .v1 import v1
    app.register_blueprint(v1)
    return app
