from . import v1
from pprika import abort
from .exception import GreenLemon


@v1.route('/lemons/<string:name>')
def lemon(name):
    print(name)
    green = GreenLemon()
    print(green)
    raise green
