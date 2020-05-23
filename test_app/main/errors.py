from . import main


@main.app_error_handler(ZeroDivisionError)
def zero_division(e):
    print(e)
    return '除零不可取: %r ' % e


@main.error_handler(IndexError)
def index_error(e):
    print(e)
    return '不存在这个索引: %r ' % e
