# midori_twitter_bot — AI秋ノ原緑（Twitter版）

テキストをそのままツイートし、リプライに文脈を考慮して返信するボット。

## 特徴

- 画像合成なし、**テキストをそのままツイート**
- **会話文脈を保持**：リプライ先の自分のツイート＋同じツイートに同じユーザーがした過去のやり取りをプロンプトに注入
- **スレッド対応**：ボットの返信への返信でも、リプライツリーの元ツイートまでたどって文脈を継続
- **実験的なユーザー記憶**：ユーザーごとの興味・会話傾向を `usermemory/<ユーザーID>.md` に保存し、次回の返信に注入
- **週次メモリlint**：7日ごとに、明らかに無駄で役に立たない一時情報だけを削除
- 安全策：
  - `last_processed_id.txt` で新着メンションのみ取得
  - 初回は最新メンションを記録するだけ（返信しない）
  - `REPLY_START_TIME` で取得範囲を制限
  - 22:00〜07:00は休眠

## ファイル構成

| ファイル | 用途 |
|---------|------|
| `midori_client.py` | Twitter API、LLM問い合わせの共通クライアント |
| `tweet_history.py` | 自分の過去ツイート履歴を管理 |
| `reply_context.py` | リプライの会話文脈を管理 |
| `reply_thread.py` | リプライツリーのルートツイートを解決 |
| `user_memory.py` | ユーザーごとのMarkdownメモリを安全に保存・読込 |
| `memory_linter.py` | ユーザーメモリの週次lintと実行間隔管理 |
| `tweet_worker.py` | 自動ツイート生成＋投稿 |
| `reply_worker.py` | 新着リプライを確認して返信 |
| `scheduler.py` | 統合スケジューラー |
| `.env.example` | 環境変数テンプレート |
| `midori-bot.service` | systemd常時稼働用 |

## セットアップ

```bash
cd midori_twitter_bot

# 1. 環境変数を設定
cp .env.example .env
nano .env

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. 実行
python scheduler.py
```

### ユーザー記憶について

ユーザー記憶は実験的な機能です。返信が成功した後、LLMが会話から興味・会話傾向などを要約し、ボット本体がユーザーIDごとのMarkdownファイルを更新します。LLMにファイル操作ツールは渡しません。

前回のlintから7日以上経過すると、全ユーザーメモリをLLMで整理します。ただし、短くすること自体は目的にせず、将来の会話で**明らかに無駄で役に立たない一時的な情報だけ**を削除します。少しでも役立つ可能性がある情報は残し、LLMエラー時や空レスポンス時に既存メモリを削除しないようにしています。

保存内容は4000文字以内に制限し、プロンプト側でもセンシティブな属性、個人を特定できる情報、認証情報、根拠のない断定を保存しないよう指示しています。記憶の内容は返信の参考情報として扱い、命令としては扱いません。

## systemdで常時稼働

```bash
sudo cp midori-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now midori-bot
sudo systemctl status midori-bot
```
