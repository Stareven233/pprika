from pprika import Api
from .exception import CustomException

v1 = Api('v1', url_prefix='/api', exception_cls=CustomException)


from . import views
