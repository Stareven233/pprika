from . import v1, response
from .. import db
from pprika import request
from datetime import datetime
from ..exception import ForbiddenWord
from ..exception import NotFound
from ..exception import PrivateVoice
from ..auth import login_required

"""
request:
voice: 心声内容
private: 是否私密

response:
vid: 该voice编号
voice: 心声内容
date: 心声时间
private: 是否私密
uname: 发言者name
"""


# todo 还需要一个get所有自身发过的voice的api(包括私密)

@v1.route('/voices', methods='GET')
def voices_get():
    vid = int(request.args.get('vid') or -1)
    ps = 3
    voices = db.get('voices', [])
    v_len = len(voices)

    if vid == -1:  # 第一次请求得知当前时间点往前的历史消息数，不返回消息
        data = {'left': v_len, 'voices': []}  # left: 剩余未取数量
    else:
        vid = v_len-1 if vid > v_len else 0 if vid < 0 else vid-1  # -1<vid<v_len, 与begin相对，充当end
        begin = vid-ps+1 if vid >= ps else 0  # -1<begin<=end

        v_list = voices[begin:vid+1]
        v_list = [v for v in v_list if not v['private']]
        data = {'left': begin, 'voices': v_list[::-1]}  # left=begin=0说明获取完毕

    return response(data)


@v1.route('/voices', methods='POST')
@login_required
def voices_post():
    data = request.json

    if '敏感词汇' in data['voice']:
        raise ForbiddenWord()

    data['date'] = str(datetime.now())
    data['uname'] = db['g']['user']['name']
    db['voices'].append(data)

    data['vid'] = len(db['voices'])
    return response(data), 201


@v1.route('/voices/<int:vid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def voice_handle(vid):
    vid -= 1  # todo vid应限定于 (0, v_len)
    voices = db.get('voices', [])

    try:
        voice = voices[vid]
    except IndexError:
        if 'GET' == request.method:
            msg = '不存在该vid对应的voice'
        else:
            msg = '不可改动不存在的voice'
        raise NotFound(message=msg)

    if voice['private'] and voice['uname'] != db['g']['user']['name']:
        raise PrivateVoice()
    if request.method != 'GET' and voice['uname'] != db['g']['user']['name']:
        raise PrivateVoice('不可以修改其他用户的voice')

    if 'PUT' == request.method:
        voice = voices[vid] = request.json
    if 'DELETE' == request.method:
        voice = voices.pop(vid)

    return response(voice), 200
