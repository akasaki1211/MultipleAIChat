import os
import json
import re

import openai

from .console import Console
from .retry import retry_decorator
from .prompts import (
    WHO_IS_TALKING_TO_SYSTEM_TEMPLATE,
    WHO_IS_TALKING_TO_USER_TEMPLATE,
    SUMMARIZE_TEMPLATE
)

openai.api_key = os.getenv('OPENAI_API_KEY')


class Interlocutor(object):

    def __init__(self, logger=None) -> None:
        
        self.logger = logger
    
    def __log(self, msg:str, lv='info'):
        if not self.logger:
            return
        self.logger(msg, cls=self, lv=lv)

    def guess(self, template:dict, input:str):
        system_prompt = WHO_IS_TALKING_TO_SYSTEM_TEMPLATE.format(template=json.dumps(template, indent=2, ensure_ascii=False))
        self.__log('Create system prompt: \n{}'.format(system_prompt), lv='debug')

        user_prompt = WHO_IS_TALKING_TO_USER_TEMPLATE.format(input=input)
        self.__log('Create user prompt: \n{}'.format(user_prompt), lv='debug')
        
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        self.__log('Guess who is input talking to...')

        # APIコール
        try:
            result = self.__completion(messages)
        except Exception as e:
            self.__log('Guess failure', lv='error')
            self.__log(str(e), lv='error')
            return
        
        interlocutor, usage = result

        # ' -> " 置換
        interlocutor = re.sub(r"'", '"', interlocutor)

        # {}抽出
        match = re.search(r'{.*}', interlocutor)
        if match:
            interlocutor = match.group(0)

        # str -> dict
        try:
            interlocutor_dict = json.loads(interlocutor)
        except Exception as e:
            self.__log('Guess result type is not dict : {}'.format(interlocutor), lv='error')
            interlocutor_dict = None

        self.__log('Guess result: {}'.format(interlocutor_dict), lv='debug')

        usage_msg = '{3} letters / {0} prompt + {1} completion = {2} tokens'.format(
                        usage['prompt_tokens'], 
                        usage['completion_tokens'], 
                        usage['total_tokens'], 
                        int(len(interlocutor))
                    )
        self.__log(usage_msg)

        return interlocutor_dict, usage

    @retry_decorator
    def __completion(self, messages:list) -> str:
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0
        )
        data = response.choices[0].message.content
        
        return data, response['usage']

class Conversations(object):
    """会話クラス

    ・会話データの保持、保存。
    ・APIに送るためのmessageリストもこのクラスが生成。
    ・一定の長さを超えると（gpt-3.5-turboで）前半を要約する機能を持つ。
    
    """

    def __init__(self, log_dir:str, session_id:str, verbose:bool=False, logger=None):
        
        self.verbose = verbose
        self.console = Console()
        self.console.set_default_color("blue")
        self.logger = logger
        
        # 会話データディレクトリ
        self.conv_dir = os.path.join(os.path.abspath(log_dir), session_id, 'conversations')
        if not os.path.isdir(self.conv_dir):
            os.makedirs(self.conv_dir)
        
        # セッション全体の会話履歴データ。名前と発言内容とそれまでの要約。
        self._session_data = []

        self.current_start_index = 0 # 現在（未要約ぶん）の開始地点
        self.prev_summary_index = None # None = prev_summaryが無い

        self.__log('Init')
    
    def __verbose(self, msg:str, col:str='', force:bool=False):
        if self.verbose or force:
            self.console(msg, col=col)

    def __log(self, msg:str, lv='info'):
        if not self.logger:
            return
        self.logger(msg, cls=self, lv=lv)

    @property
    def session_data(self):
        return self._session_data
    
    @property
    def prev_summary(self):
        if type(self.prev_summary_index) == int:
            return self._session_data[self.prev_summary_index]["summary_so_far"]
        else:
            return ''
        
    @property
    def lines_of_conversations(self):
        # current_start_index ~ 最後-1までの会話履歴
        return self.__create_conv_lines(start=self.current_start_index, end=int(len(self._session_data))-1)

    def __log_data_length(self):
        s = 'session data len: {} / current start index: {} / prev summary index: {}'.format(
            len(self._session_data),
            self.current_start_index,
            self.prev_summary_index
        )
        self.__log(s)
    
    def add_content(self, name:str, content:str):
        
        self.__log('Add new content ({}:{})'.format(name, content))

        data = {"name":name, 
                "content": content, 
                "summary_so_far":"", 
                "summary_usage":{}
                }
        
        # 新しい要素の追加
        self._session_data.append(data)

        self.__log_data_length()

        self.export_session_data()

    def check_current_lengh(self, max:int):
        current_length = int(len(self._session_data)) - self.current_start_index
        
        # 長さが max に達しているかどうかを返す
        return current_length >= max

    def shrink_messages(self, summarize:int):
        """現在の開始地点からsummarize数ぶんの会話を要約し、データとindexを更新する

        Args:
            summarize (int): 要約する発言数。-1だった場合は残りすべて。
        """
        
        if summarize == -1:
            summarize_end_index = int(len(self._session_data)) - 1
        else:
            summarize_end_index = self.current_start_index + summarize - 1

        # 要約する長さ再計算
        summarize_len = summarize_end_index + 1 - self.current_start_index
        if summarize_len:
            msg = 'Shrink current... (summarize length:{})'.format(summarize_len)
            self.__log(msg)
        else:
            # 長さがゼロだったら何もしない
            msg = 'No shrink (summarize length:{})'.format(summarize_len)
            self.__log(msg)
            return
        
        # 要約用に前半を抽出
        lines = self.__create_conv_lines(start=self.current_start_index, end=summarize_end_index + 1)

        # 要約
        msg = 'Start summarising... ({} lines)'.format(summarize_len)
        self.__verbose(msg, col="yellow")
        self.__log(msg)

        # APIコール
        try:
            summarize_result = self.__summarize_completion(self.prev_summary, lines)
        except Exception as e:
            self.__verbose('Summarization failure', col="red", force=True)
            self.__log('Summarization failure', lv='error')
            self.__log(str(e), lv='error')
            return
        
        new_summary, usage = summarize_result
        
        self.__verbose('Summarization complete : {}'.format(new_summary), col="yellow")
        self.__log('Summarization complete : {}'.format(new_summary))

        usage_msg = '{3} letters / {0} prompt + {1} completion = {2} tokens'.format(
                        usage['prompt_tokens'], 
                        usage['completion_tokens'], 
                        usage['total_tokens'], 
                        int(len(new_summary))
                    )
        
        self.__log(usage_msg)

        # 要約結果をsession_dataに格納
        self._session_data[summarize_end_index]["summary_so_far"] = new_summary
        self._session_data[summarize_end_index]["summary_usage"] = usage

        # 各indexを更新
        self.current_start_index = summarize_end_index + 1
        self.prev_summary_index = summarize_end_index

        self.export_session_data()
        
        self.__log_data_length()

    def __create_conv_lines(self, start:int=0, end=None) -> str:
        lines = []
        for msg in self._session_data[start:end]:
            lines.append('{} : {}'.format(msg['name'], msg['content']))
        
        return '\n'.join(lines)
    
    @retry_decorator
    def __summarize_completion(self, prev_summary:str="", new_lines:str="") -> str:
        
        prompt = SUMMARIZE_TEMPLATE.format(summary=prev_summary, new_lines=new_lines)
        
        self.__log('Summarize prompt :\n{}'.format(prompt), lv='debug')
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}], 
            temperature=0
        )
        summary = response.choices[0].message.content
        
        return summary, response['usage']
    
    def __export_json(self, dict:dict, path:str):
        self.__log('Export : {}'.format(path))

        with open(path, 'w', encoding='utf-8-sig') as f:
            json.dump(dict, f, indent=4, ensure_ascii=False)

    def __export_txt(self, data, path:str):
        self.__log('Export : {}'.format(path))

        with open(path, 'w', encoding='utf-8-sig') as f:
            if type(data) == list:
                f.writelines(data)
            elif type(data) == str:
                f.write(data)

    def export_session_data(self):
        file_path = os.path.join(self.conv_dir, 'session_data.json')
        self.__export_json(self._session_data, file_path)

        file_path = os.path.join(self.conv_dir, 'talk_history.txt')
        self.__export_txt(self.__create_conv_lines(), file_path)