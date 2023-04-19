import os
import json
import requests
import wave
import pyaudio
import socket
import subprocess
import re
import alkana

with open('settings.json', mode="r", encoding="utf-8") as f:
    settings_dict = json.load(f)

VOICEVOX_ENGINE_PATH = settings_dict["voicevox"]["engine_path"]

class VoiceGenerator(object):

    def __init__(self, logger=None):
        self.logger = logger
        self.__log('Init')
        
        self.chunk_size = 1024

        if VOICEVOX_ENGINE_PATH:
            if not self.__check_server('localhost', 50021):
                subprocess.Popen(['start', '', VOICEVOX_ENGINE_PATH, '--use_gpu'], shell=True)
    
    def __log(self, msg:str, lv='info'):
        if not self.logger:
            return
        self.logger(msg, cls=self, lv=lv)

    def __check_server(self, address, port):
        s = socket.socket()
        try:
            s.connect((address, port))
            return True
        except ConnectionRefusedError:
            return False
        finally:
            s.close()
    
    def __alkana(self, text:str) -> str:
        
        pattern = r'[a-zA-Z]+'
        words = re.findall(pattern, text)
        
        for w in words:
            kana = alkana.get_kana(w)
            if kana:
                text = re.sub(w, kana, text)

        return text

    def text2voice(self, text, 
                    filename, 
                    path='wav', 
                    speaker=0, 
                    volume=1, 
                    speed=1.0, 
                    pitch=0, 
                    intonation=1,
                    post=0) -> str:
        
        text = self.__alkana(text)
        
        self.__log('Start voice synthesis... ({})'.format(text))

        # audio_query
        res1 = requests.post("http://localhost:50021/audio_query",
                            params={"text": text, "speaker": speaker})
        
        res1 = res1.json()
        res1["volumeScale"]=volume
        res1["speedScale"]=speed
        res1["pitchScale"]=pitch
        res1["intonationScale"]=intonation
        res1["postPhonemeLength"]=post
        
        # synthesis
        res2 = requests.post("http://localhost:50021/synthesis",
                            params={"speaker": speaker},
                            data=json.dumps(res1))
        
        if not os.path.isdir(path):
            os.makedirs(path)
        
        audio_file = os.path.join(path, filename + '.wav')
        with open(audio_file, mode="wb") as f:
            f.write(res2.content)

        self.__log('Complete synthesis : {}'.format(audio_file))

        return audio_file

    def play_wave(self, wav:str, delete=False):
        if not os.path.isfile(wav):
            return
        
        self.__log('Play : {}'.format(wav))

        with wave.open(wav, mode='r') as wf:

            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            data = wf.readframes(self.chunk_size)
            while data != b'':
                stream.write(data)
                data = wf.readframes(self.chunk_size)

            stream.stop_stream()
            stream.close()
            p.terminate()

        if delete:
            os.remove(wav)
            self.__log('Delete file : {}'.format(wav))
