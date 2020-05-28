from . import v1, response
from .. import db
from datetime import datetime
from ..exception import ForbiddenWord
from ..exception import NotFound
from ..exception import PrivateVoice
from ..auth import login_required
from pprika import Resource
from pprika import RequestParser

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


class VoiceList(Resource):
    decorators = [login_required]

    def __init__(self):
        self.reqparse = RequestParser()

    def get(self):
        self.reqparse.add_argument('vid', type=int, default=-1, location='args')
        self.reqparse.add_argument('ps', type=int, default=3, location='args')
        args = self.reqparse.parse_args(strict=True)
        vid, ps = args['vid'], args['ps']

        voices = db.get('voices', [])
        v_len = len(voices)

        if vid == -1:  # 第一次请求得知当前时间点往前的历史消息数，不返回消息
            data = {'left': v_len, 'voices': []}  # left: 剩余未取数量
        else:
            vid = v_len-1 if vid > v_len else 0 if vid < 0 else vid-1  # -2<vid<v_len, 与begin相对，充当end
            begin = vid-ps+1 if vid >= ps else 0  # -1<begin<=vid
            data = {'left': begin, 'voices': []}

            v_list = voices[begin:vid+1]
            v_list = [v for v in v_list if not v['private']]  # 隐私项会被过滤
            data['voices'] = v_list[::-1]  # left=begin=0说明获取完毕

        return response(data)

    def post(self):
        self.reqparse.add_argument('voice', type=str, required=True, location='json')
        self.reqparse.add_argument('private', type=int, default=0, location='json')
        data = self.reqparse.parse_args(strict=True)

        if '敏感词汇' in data.voice:
            raise ForbiddenWord()

        data['date'] = str(datetime.now())
        data['uname'] = db['g']['user']['name']
        db['voices'].append(data)

        data['vid'] = len(db['voices'])
        return response(data), 201


class Voice(Resource):
    decorators = [login_required]

    def get(self, vid):
        vid -= 1  # todo vid应限定于 (0, v_len)
        voices = db.get('voices', [])

        try:
            voice = voices[vid]
        except IndexError:
            raise NotFound(message='不存在该vid对应的voice')

        if voice['private'] and voice['uname'] != db['g']['user']['name']:
            raise PrivateVoice()

        return response(voice), 200

    def put(self, vid):
        reqparse = RequestParser()
        reqparse.add_argument('private', type=int, default=0, location='json')
        args = reqparse.parse_args()

        vid -= 1
        voices = db.get('voices', [])

        try:
            voice = voices[vid]
        except IndexError:
            raise NotFound(message='不可修改不存在的voice')

        if voice['uname'] != db['g']['user']['name']:
            raise PrivateVoice(message='不可修改其他用户的voice')

        data = voices[vid]
        data['date'] = str(datetime.now())
        data.update(args)

        return response(data), 200

    def delete(self, vid):
        vid -= 1
        voices = db.get('voices', [])

        try:
            voice = voices[vid]
        except IndexError:
            raise NotFound(message='不可删除不存在的voice')

        if voice['uname'] != db['g']['user']['name']:
            raise PrivateVoice(message='不可删除其他用户的voice')

        voice = voices.pop(vid)
        return response(voice), 200


v1.add_resource(VoiceList, '/voices')
v1.add_resource(Voice, '/voices/<int:vid>')
