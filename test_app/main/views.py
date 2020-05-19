from . import main


@main.route('/mao', endpoint='hei')
@main.route('/cat', methods=['GET', 'POST'])
def get_ero():
    return '喵喵!!喵喵喵喵是猫'


main.add_url_rule('/ero', 'ero', get_ero)
# 对同一函数两次绑定的endpoint不同无妨
