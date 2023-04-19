# 複数AIと会話する実験

## 環境構築
```
python -m venv venv
.\venv\scripts\activate

pip install -r requirements.txt
```

## 実行
`-c`の後ろに登場させるキャラ名を複数連ねて開始します。  
実行後まず何らかのユーザー入力を行うと会話が始まりますが、AI同士が話し始めるかどうかは運次第です。  
```
python run.py -c dereko interiko
```

> **Note**  
> `exit`を入力すると終了します。

オプション :
```
usage: run.py [-h] [-c [CHARACTER ...]] [-v VERBOSE]

options:
  -h, --help            show this help message and exit
  -c [CHARACTER ...], --character [CHARACTER ...]
                        キャラクター名。複数指定可。
  -v VERBOSE, --verbose VERBOSE
                        コンソールに情報を出力
```

## キャラクターデータ
以下のように`character_data`階層の下に各キャラの名前(ID)フォルダがあり、その中にペルソナ情報が入っています。`run.py`の`-c`オプションにはこのIDを指定します。
```
MultipleAIChat
└─character_data
    ├─dereko
    │       settings.json
    │       talksample.txt
    │       talkstyle.txt
    │
    └─interiko
            settings.json
            talksample.txt
            talkstyle.txt
```


### 解説
[AIキャラ同士の会話に僭越ながら人間1名ほど参加させていただく](https://qiita.com/akasaki1211/items/fe5182da2cf88dc87ee5)  

### 声
[VOICEVOX ENGINE](https://github.com/VOICEVOX/voicevox_engine)  