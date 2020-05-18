from pprika import PPrika


def create_app():
    app = PPrika()
    from .main import main
    app.register_blueprint(main)
    return app
