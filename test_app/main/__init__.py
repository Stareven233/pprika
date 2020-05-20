from pprika import Blueprint

main = Blueprint('main', '/')
# the __name__ in main.__init__:  test_app.main


from . import views, errors
