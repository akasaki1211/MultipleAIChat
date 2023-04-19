import os
import argparse
import json
import random
import time
from datetime import datetime
import queue
from concurrent.futures import ThreadPoolExecutor

from ai_character import *

WAV_PATH = os.getenv('TEMP')

with open('settings.json', mode="r", encoding="utf-8") as f:
    settings_dict = json.load(f)

USERNAME = settings_dict["username"]

CHARACTER_DATA_PATH = os.path.abspath(settings_dict["character_dir"])
LOG_PATH = os.path.abspath(settings_dict["log_dir"])

EXIT_KEY = settings_dict["exit_key"]

CONV_MAX = settings_dict["conversation"]["max"]
CONV_SUMMARIZE = settings_dict["conversation"]["summarize"]

V_VOL = settings_dict["voicevox"]["volume"]
V_POST = settings_dict["voicevox"]["post"]



class CharacterData(object):

    def __init__(self, ch_id:str, 
                log_dir:str, 
                session_id:str, 
                verbose:bool=False, 
                logger=None):

        self._ch_id = ch_id
        
        self._character = Character(character_data_path=CHARACTER_DATA_PATH, 
                            ch_id=ch_id, 
                            log_dir=log_dir,
                            session_id=session_id,
                            verbose=verbose, 
                            logger=logger)
        
    @property
    def id(self):
        return self._ch_id
    
    @property
    def character(self):
        return self._character

class Message(object):

    def __init__(self, name:str, content:str):

        self._name = name
        self._content = content
    
    @property
    def name(self):
        return self._name
    
    @property
    def content(self):
        return self._content

class MultiCharacterTalking(object):

    def __init__(self, ch_id_list:list, verbose:bool=False):
        
        if not ch_id_list:
            return
        
        # global settings
        self.username = USERNAME
        self.session_id = datetime.now().strftime('s_%y%m%d_%H%M%S')
        self._exit_flag = False

        # console
        self.verbose = verbose
        self.console = Console()
        self.console.set_default_color("yellow")

        # logger
        self.logger = Logger(logdir=os.path.join(LOG_PATH, self.session_id), filename=self.session_id+'.log')

        # init characters
        self.ch_dict = {}
        for ch_id in ch_id_list:
            ch_data = CharacterData(ch_id, 
                                log_dir=LOG_PATH, 
                                session_id=self.session_id, 
                                verbose=verbose, 
                                logger=self.logger)
            self.ch_dict[ch_data.character.name] = ch_data

        # init conversations
        self.q_user_input = queue.Queue(3)
        self.q_message = queue.Queue(1)
        self.conv = Conversations(log_dir=LOG_PATH,
                            session_id=self.session_id, 
                            verbose=verbose, 
                            logger=self.logger)
        
        self.interlocutor_template = {}
        self.interlocutor_template[self.username] = 0.0
        for ch_name in self.ch_dict.keys():
            self.interlocutor_template[ch_name] = 0.0
        self.interlocutor_template["unknown"] = 1.0

        self.interlocutor = Interlocutor(logger=self.logger)
        
        # init voice
        self.voice_generator = VoiceGenerator(logger=self.logger)
        self.q_voice_play = queue.Queue(1) #これ増やすとcompletionがどんどん先行するので注意
        
        self.main()

    def main(self):

        executor = ThreadPoolExecutor()
        future_list = []

        self.logger('Submit talk_thread.', cls=self, fn=self.main)
        future_list.append(executor.submit(self.talk_thread, 
                                                self.conv))
        
        self.logger('Submit manage_conv_thread.', cls=self, fn=self.main)
        future_list.append(executor.submit(self.manage_conv_thread, 
                                            self.conv))

        self.logger('Submit voice_play_thread.', cls=self, fn=self.main)
        future_list.append(executor.submit(self.voice_play_thread, 
                                            self.voice_generator))

        self.logger('Submit user_input_thread.', cls=self, fn=self.main)
        future_list.append(executor.submit(self.user_input_thread))

        self.logger('Thread Count : {}'.format(len(future_list)), cls=self, fn=self.main)
        
        executor.shutdown(wait=True)
        
        self.logger('Exit', cls=self, fn=self.main)

    def user_input_thread(self):
        """ユーザー入力を受け取り、キューにアイテムを追加する。"""
        
        while True:
            self.logger('Waiting for user input...', cls=self, fn=self.user_input_thread)
            user_input = input()

            if not user_input:
                continue
            
            if user_input == EXIT_KEY:
                self.logger('==== Command exit ====', cls=self, fn=self.user_input_thread)
                self._exit_flag = True
                break
            
            self.logger('Put item to user message queue {}:{}'.format(self.username, user_input), cls=self, fn=self.user_input_thread)
            self.q_user_input.put(Message(name=self.username, content=user_input))
            self.logger('user message queue size: {}'.format(self.q_user_input.qsize()), cls=self, fn=self.user_input_thread)
        
        self.logger('Exit', cls=self, fn=self.user_input_thread)
    
    def talk_thread(self, conv:Conversations):
        """
            キューから発言を取り出し、発言者以外で誰が応答すべきかを判定、その後返答を作成する。
            得られた返答は発言キューとボイス再生キューに追加する。
        """

        while not (self._exit_flag and self.q_message.empty()):
            """
                アイテムが取り出せるまで、1秒おきにチェック。
                _exit_flagがTrueかつ、AI用メッセージキューが空になると抜ける。
            """

            current_queue_list = []

            try:
                # AIの発言をキューから取得
                ai_msg = self.q_message.get(timeout=1)
                current_queue_list.append(self.q_message)
            except queue.Empty:
                ai_msg = False
            
            try:
                # ユーザーの発言をキューから取得
                user_msg = self.q_user_input.get(timeout=1)
                current_queue_list.append(self.q_user_input)
            except queue.Empty:
                user_msg = False

            # ユーザー発言もAI発言もどちらもなければcontinue
            if not (ai_msg or user_msg):
                continue
            
            # log
            self.logger('Get item count : {}'.format(len([x for x in [ai_msg, user_msg] if x])), cls=self, fn=self.talk_thread)
            
            # AIの発言を会話データに追加
            if ai_msg:
                self.logger('Get item : {}:{}'.format(ai_msg.name, ai_msg.content), cls=self, fn=self.talk_thread)
                conv.add_content(name=ai_msg.name, content=ai_msg.content)
            
            # ユーザーの発言を会話データに記録　※キューに足されたタイミングがどうであれ、ユーザーの発言を後ろにする。
            if user_msg:
                self.logger('Get item : {}:{}'.format(user_msg.name, user_msg.content), cls=self, fn=self.talk_thread)
                conv.add_content(name=user_msg.name, content=user_msg.content)
                
            # ユーザーとAI発言両方来た場合、ユーザーの発言を最新としてCompletionする。
            msg = user_msg if user_msg else ai_msg

            # 誰が応答すべきか、発言者以外の中から判別する
            new_template = dict(self.interlocutor_template)
            del new_template[msg.name]

            interlocutor_dict, usage = self.interlocutor.guess(new_template, msg.content)

            if interlocutor_dict:
                interlocutor_key = max(interlocutor_dict, key=interlocutor_dict.get)
            else:
                interlocutor_key = "unknown"

            # 判別不能（unknown）だった場合、発言者以外のAIキャラからランダム抽選する
            if interlocutor_key == "unknown":
                self.logger('Next is unknown. Random choice...', cls=self, fn=self.talk_thread)
                ch_name_list = list(self.ch_dict.keys())
                if msg.name in ch_name_list:
                    ch_name_list.remove(msg.name)
                interlocutor_key = random.choice(ch_name_list)

            # 次に誰が話すか決定
            self.logger('Next : {}'.format(interlocutor_key), cls=self, fn=self.talk_thread)
            if self.verbose:
                self.console(" -> {}".format(interlocutor_key))
            if not interlocutor_key in self.ch_dict.keys():
                # AIキャラクターじゃなかったらここでcontinue
                for current_queue in current_queue_list:
                    current_queue.task_done()
                continue

            ch = self.ch_dict[interlocutor_key].character
            
            # messages作成（内部でsystemプロンプトとuserプロンプトを生成）
            messages = ch.create_messages(
                        user_input=msg.content, 
                        user_name=msg.name, 
                        talk_summary=conv.prev_summary, 
                        lines_of_conversations=conv.lines_of_conversations)
            
            # completion
            result = ch.talk(messages)
            if result:
                ai_content, token_usage = result
            else:
                # リトライしても応答がなかった場合、発言無しとして""を入れる。
                ai_content = ""

            # AIの発言をキューに追加（音声合成用）
            # __voice_synthesis内、再生キューにputするところでCompletionだけが進みすぎないようにブロックしてる。
            # 再生キューのサイズを無限にしちゃうとCompletionだけどんどん先に進むので注意。
            self.__voice_synthesis(ch, ai_content)
            
            # AIの発言をAIメッセージキューに追加（次の人に渡すため）
            # ※exitになったときはキューに入れず（他者に渡さず）終える。キューを空にしないとループ抜けられないので。。。
            if not self._exit_flag:
                self.logger('[{}] Put item to message queue: {}'.format(ch.id, ai_content), cls=self, fn=self.talk_thread)
                self.q_message.put(Message(name=ch.name, content=ai_content))
                self.logger('message queue size: {}'.format(self.q_message.qsize()), cls=self, fn=self.talk_thread)

            for current_queue in current_queue_list:
                current_queue.task_done()
        
        self.logger('Exit', cls=self, fn=self.talk_thread)

    def manage_conv_thread(self, conv:Conversations):

        while not self._exit_flag:
            # 3秒おきにsession_dataの長さをチェックして要約が必要か判断
            time.sleep(3)
            
            do_shrink = conv.check_current_lengh(CONV_MAX)
            if not do_shrink:
                continue

            conv.shrink_messages(CONV_SUMMARIZE)
            
        #conv.shrink_messages(-1) # 残りすべて要約して終了
        
        self.logger('Exit', cls=self, fn=self.manage_conv_thread)

    def voice_play_thread(self, v:VoiceGenerator):

        while not (self._exit_flag and self.q_voice_play.empty()):
            """
            合成されたwavパスをキューから取り出す
            アイテムが取り出せるまで、1秒おきにチェック。
            _exit_flagがTrueかつ、キューが空になると抜ける
            """
            try:
                data = self.q_voice_play.get(timeout=1)
            except queue.Empty:
                continue

            wav_path = data[0]
            text = data[1]
            ch= data[2]

            self.logger('Get item : {}'.format(wav_path), cls=self, fn=self.voice_play_thread)

            # ボイス再生の直前にコンソール出力
            ch.console('{} : {}'.format(ch.name, text))

            # 再生
            v.play_wave(wav=wav_path, delete=True)
        
        self.logger('Exit', cls=self, fn=self.voice_play_thread)

    def __voice_synthesis(self, ch:Character, text:str):
        """受け取ったテキストで音声合成し、得られたwavをキューに追加する。"""

        wav_path = self.voice_generator.text2voice(text, 
                                str(time.time()), 
                                path=WAV_PATH, 
                                speaker=ch.voice_speaker_id,
                                speed=ch.voice_speed,
                                pitch=ch.voice_pitch,
                                intonation=ch.voice_intonation, 
                                volume=V_VOL,
                                post=V_POST)
        
        self.q_voice_play.put([wav_path, text, ch])


if __name__ == "__main__":

    try:
        os.environ['OPENAI_API_KEY']
    except KeyError:
        print(u'OPENAI_API_KEY が設定されていません。')
    else:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-c", "--character",
            type=str,
            nargs='*',
            default=[],
            help="キャラクター名。複数指定可。",
        )

        parser.add_argument(
            "-v", "--verbose",
            type=bool,
            default=False,
            help="コンソールに情報を出力",
        )

        opt = parser.parse_args()

        MultiCharacterTalking(ch_id_list=opt.character, verbose=opt.verbose)