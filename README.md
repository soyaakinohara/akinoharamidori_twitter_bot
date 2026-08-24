# 秋ノ原緑 Twitter bot

Twitter APIとローカルLLMを使って、秋ノ原緑として定期ツイートと返信を行うボットです。

## できること

- `scheduler.py` が2時間ごとにツイートし、10分後に新着リプライを確認する
- 返信の文脈を「会話の起点となるツイート × リプライしたユーザー」ごとに分けて保持する
- ボットの返信への返信でも、スレッドの元ツイートまでたどって会話を続ける
- ユーザーごとの興味や会話傾向を `usermemory/<ユーザーID>.md` に保存する
- 会話の内容からユーザーの情報を記憶し、それに合った返事をします
- 7日ごとに、明らかに不要な一時情報だけをユーザーメモリから削る

## セットアップ

```bash
cp .env.example .env
# .env にTwitter APIとLLMの設定を記入
pip install -r requirements.txt
python scheduler.py
```

主な設定項目は `.env.example` にあります。`REPLY_START_TIME` を指定すると、リプライの取得開始時刻を変更できます。

## メモリの扱い

短期的な会話履歴と、ユーザーごとの長期メモリを分けて管理します。

- 短期履歴: `reply_context.json` にツイートとユーザーの組み合わせごとに保存
- 長期メモリ: `usermemory/<ユーザーID>.md` に保存
- 長期メモリは返信成功後にLLMが更新し、ファイル書き込みはボット本体が行う
- 週次lintは、少しでも役立つ可能性がある情報を残し、明らかに無駄な情報だけを削除する
- メモリは4000文字以内。LLMのエラーや空レスポンスで既存データを消さない

ユーザー記憶は実験的な機能です。公開アカウントの会話から作られるため、必要に応じて `usermemory/` の内容を確認・削除してください。実行時データと認証情報は `.gitignore` で公開対象から外しています。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `scheduler.py` | 定期ツイートとリプライ確認を実行 |
| `reply_worker.py` | リプライ確認を単独で実行 |
| `midori_client.py` | Twitter APIとLLMへの接続 |
| `reply_context.py` | ツイート×ユーザー単位の短期履歴 |
| `reply_thread.py` | スレッドの元ツイートを解決 |
| `user_memory.py` | ユーザーメモリの保存と読込 |
| `memory_linter.py` | 週次lintと実行間隔の管理 |
| `.env.example` | 設定ファイルのテンプレート |

## テスト

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

## systemdで常時稼働

```bash
sudo cp midori-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now midori-bot
```
