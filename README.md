# 複数AIと会話

## 環境構築
```
python -m venv venv
.\venv\scripts\activate

pip install -r requirements.txt
```

## 実行
```
python run.py -c setoka kurumi
```
↓情報表示アリ
```
python run.py -c setoka kurumi -v True
```
ユーザー発言の代わりに`exit`を入力すると終了します。放っておくとトークンをどんどん消費するのでご注意ください。

## リンク
解説：[]()
声：[VOICEVOX ENGINE](https://github.com/VOICEVOX/voicevox_engine)