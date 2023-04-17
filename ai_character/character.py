import os
import json
import random
import openai

from .console import Console
from .retry import retry_decorator
from .prompts import (
    SYSTEM_TEMPLATE, 
    CONVERSATION_USER_TEMPLATE
)

openai.api_key = os.getenv('OPENAI_API_KEY')

with open('settings.json', mode="r", encoding="utf-8") as f:
    settings_dict = json.load(f)

MODEL_NAME = settings_dict["talk"]["completion"]["model"]
TEMPERATURE = settings_dict["talk"]["completion"]["temperature"]
TOP_P = settings_dict["talk"]["completion"]["top_p"]
P_PENALTY = settings_dict["talk"]["completion"]["presence_penalty"]
F_PENALTY = settings_dict["talk"]["completion"]["frequency_penalty"]

RESPONSE_MIN = settings_dict["talk"]["response_min"]
RESPONSE_MAX = settings_dict["talk"]["response_max"]

class Character(object):

    def __init__(self, 
                    character_data_path:str, 
                    ch_id:str, 
                    log_dir:str, 
                    session_id:str, 
                    verbose:bool=False, 
                    logger=None):

        self.verbose = verbose
        self.console = Console()
        self.logger = logger
        
        # キャラデータディレクトリ
        self.id = ch_id
        self.data_dir = os.path.abspath(os.path.join(character_data_path, ch_id))
        
        # ペルソナ情報
        self.name = ""
        self.profile = ""
        self.talksample = ""
        self.talkstyle = ""
        self.voice_speaker_id = 0
        self.voice_speed = 0
        self.voice_pitch = 0
        self.voice_intonation = 0
        
        # ペルソナデータの読み込み
        self.__log('Load Character ...')
        if not self.__load_character():
            return
        
        # Completionログディレクトリ
        self.comp_log_dir = os.path.join(os.path.abspath(log_dir), session_id, 'completions')
        if not os.path.isdir(self.comp_log_dir):
            os.makedirs(self.comp_log_dir)
        
        # Completion履歴。送ったmessagesと、返ってきた文、使用トークン数
        self.completion_log = []

    def __verbose(self, msg:str, col:str='', force:bool=False):
        if self.verbose or force:
            self.console('[{}] {}'.format(self.id, msg), col=col)

    def __log(self, msg:str, lv='info'):
        if not self.logger:
            return
        self.logger('[{}] {}'.format(self.id, msg), cls=self, lv=lv)

    def __load_character(self):
        character_data = self.__character_loader(self.data_dir)
        
        if not character_data:
            msg = 'キャラクターデータのロードに失敗しました'
            self.__verbose(msg, col="red", force=True)
            self.__log(msg, lv='critical')
            return False
        
        profile_dict, self.talksample, self.talkstyle = character_data
        self.name = profile_dict['profile']['name']
        self.profile = self.__profile_dict_to_str(profile_dict['profile'])

        self.voice_speaker_id = int(profile_dict['voice']['speaker_id'])
        self.voice_speed = float(profile_dict['voice']['speed'])
        self.voice_pitch = float(profile_dict['voice']['pitch'])
        self.voice_intonation = float(profile_dict['voice']['intonation'])

        self.console.set_default_color(profile_dict['console_color'])

        return True
    
    def __character_loader(self, path:str):
        profile_dict = {}
        profile_path = os.path.join(path, 'settings.json')
        if os.path.isfile(profile_path):
            with open(profile_path, mode='r', encoding='utf-8-sig') as f:
                profile_dict = json.load(f)

        talksample = ""
        talksample_path = os.path.join(path, 'talksample.txt')
        if os.path.isfile(talksample_path):
            with open(talksample_path, mode='r', encoding='utf-8-sig') as f:
                talksample = f.read()

        talkstyle = ""
        talkstyle_path = os.path.join(path, 'talkstyle.txt')
        if os.path.isfile(talkstyle_path):
            with open(talkstyle_path, mode='r', encoding='utf-8-sig') as f:
                talkstyle = f.read()

        self.__log(profile_path)
        self.__log(talksample_path)
        self.__log(talkstyle_path)

        return profile_dict, talksample, talkstyle

    def __profile_dict_to_str(self, profile_dict:dict) -> str:
        profile_list = []
        for key in ["name", "age", "gender", "job"]:
            if key in profile_dict.keys():
                profile_list.append('{}:{}'.format(key, profile_dict[key]))
        for i in range(5):
            key = 'option{}'.format(i+1)
            if key in profile_dict.keys():
                if profile_dict[key]:
                    profile_list.append(profile_dict[key])

        return '\n'.join(profile_list)
    
    @retry_decorator
    def __completion(self, messages:list):
        """OpenAIのGPT-3.5モデルを使用して、ユーザーの入力に基づいてテキスト生成を行う。"""

        msg = json.dumps(messages, indent=4, ensure_ascii=False)
        self.__log('Sent message list :\n{}'.format(msg), lv='debug')

        response = openai.ChatCompletion.create(
            model=MODEL_NAME,
            temperature=TEMPERATURE, 
            top_p=TOP_P, 
            presence_penalty=P_PENALTY, 
            frequency_penalty=F_PENALTY, 
            messages=messages
        )
        ai_message_text = response.choices[0].message.content

        return ai_message_text, response['usage']

    def create_system_message(self, talk_summary:str='', lines_of_conversations:str=''):

        prompt = SYSTEM_TEMPLATE.format(profile=self.profile, 
                                                talk_sample=self.talksample, 
                                                talk_summary=talk_summary,
                                                lines_of_conversations=lines_of_conversations)
        
        self.__log('Create system prompt: \n{}'.format(prompt), lv='debug')

        system_message = {"role": "system", "content": prompt}

        return system_message
    
    def create_user_message(self, user_input:str, user_name:str='User') -> str:
        
        if not user_input:
            return
        
        # chat user prompt
        prompt = CONVERSATION_USER_TEMPLATE.format(name=self.name, 
                                            talk_style=self.talkstyle,
                                            input=user_input, 
                                            user=user_name, 
                                            words=random.randint(RESPONSE_MIN, RESPONSE_MAX))
        
        self.__log('Create user prompt: \n{}'.format(prompt), lv='debug')

        user_message = {"role": "user", "content": prompt}

        return user_message

    def create_messages(self, 
                        user_input:str, 
                        user_name:str='User', 
                        talk_summary:str='', 
                        lines_of_conversations:str=''):
        
        messages = []
        messages.append(self.create_system_message(talk_summary=talk_summary, lines_of_conversations=lines_of_conversations))
        messages.append(self.create_user_message(user_input=user_input, user_name=user_name))

        return messages

    def talk(self, messages:list) -> str:
        
        self.__verbose('Start completion...', col="yellow")
        self.__log('Start completion...')

        # APIコール
        try:
            completion_result = self.__completion(messages)
        except Exception as e:
            self.__verbose('Completion failure', col="red", force=True)
            self.__verbose("(スタッフ) {}は今考え中です！少し待ってからもう一度話しかけてみてね！".format(self.name), col="red", force=True)
            self.__log('Completion failure', lv='error')
            self.__log(str(e), lv='error')
            return
        
        ai_content, usage = completion_result

        # log
        self.__verbose("Completion response : {}".format(ai_content), col="yellow")
        self.__log('Completion response : {}'.format(ai_content))

        usage_msg = '{3} letters / {0} prompt + {1} completion = {2} tokens'.format(
                        usage['prompt_tokens'], 
                        usage['completion_tokens'], 
                        usage['total_tokens'], 
                        int(len(ai_content))
                    )

        self.__log(usage_msg)

        # completion log dict
        log = {
            "messages":messages,
            "response":{
                "content":ai_content,
                "usage":usage
            }
        }
        self.completion_log.append(log)
        self.export_completion_log()
        
        return ai_content, usage
    
    def __export_json(self, dict:dict, path:str):
        self.__log('Export : {}'.format(path))
        with open(path, 'w', encoding='utf-8-sig') as f:
            json.dump(dict, f, indent=4, ensure_ascii=False)

    def export_completion_log(self):
        file_path = os.path.join(self.comp_log_dir, '{}_completion_log.json'.format(self.id))
        self.__export_json(self.completion_log, file_path)