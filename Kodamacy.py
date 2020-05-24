from app import create_app

app = create_app()


@app.route('/')
def index():
    return {"msg": "太好了，是树洞"}, 233


if __name__ == '__main__':
    app.run('localhost', 9000, use_debugger=True)
