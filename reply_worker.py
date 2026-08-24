import os
import time
from datetime import datetime, timedelta, timezone
from midori_client import MidoriClient
from tweet_history import find_tweet_text
from reply_context import add_exchange, get_conversation_history
from reply_thread import get_included_tweets, get_root_tweet_id
from user_memory import load_user_memory, save_user_memory
from memory_linter import lint_all_memories

# --- 秋ノ原緑ボット リプライ部隊 ---
# メンションを監視し、文脈を考慮して返信する。

ID_FILE = "last_processed_id.txt"


def get_last_id():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read().strip()
    return None


def save_last_id(tweet_id):
    with open(ID_FILE, "w") as f:
        f.write(str(tweet_id))


def get_start_time(client):
    """.env で REPLY_START_TIME が指定されていれば使う。なければ24時間前。"""
    start_time = client.env.get("REPLY_START_TIME")
    if start_time:
        return start_time
    return (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    client = MidoriClient()
    lint_result = lint_all_memories(client)
    if lint_result["ran"]:
        print(
            "🧹 ユーザーメモリlint完了: "
            f"{lint_result['checked']}件確認、"
            f"{lint_result['changed']}件更新、"
            f"{lint_result['failed']}件失敗"
        )
    user_id = client.get_user_id()
    since_id = get_last_id()
    start_time = get_start_time(client)

    print(f"🕵️ 新着リプライをチェック中... (since_id: {since_id}, start_time: {start_time})")

    tweet_fields = ["created_at", "referenced_tweets"]
    expansions = ["author_id", "referenced_tweets.id"]

    if since_id:
        mentions = client.twitter.get_users_mentions(
            user_id,
            since_id=since_id,
            start_time=start_time,
            expansions=expansions,
            tweet_fields=tweet_fields
        )
    else:
        # 初回：最新メンションを取得して記録するだけ（返信しない）
        mentions = client.twitter.get_users_mentions(
            user_id,
            start_time=start_time,
            expansions=expansions,
            tweet_fields=tweet_fields,
            max_results=5
        )
        if mentions.data:
            latest_id = max(int(tweet.id) for tweet in mentions.data)
            save_last_id(latest_id)
            print(f"📌 初回実行：最新メンションID {latest_id} を記録しました。次回から返信します。")
        else:
            print("📭 新着リプライはありません。")
        return

    if not mentions.data:
        print("📭 新着リプライはありません。")
        return

    included_tweets = get_included_tweets(mentions)
    fetched_tweets = {}

    def fetch_tweet(tweet_id):
        if tweet_id in fetched_tweets:
            return fetched_tweets[tweet_id]
        try:
            response = client.twitter.get_tweet(
                tweet_id,
                tweet_fields=["referenced_tweets"]
            )
            fetched_tweets[tweet_id] = response.data
        except Exception as e:
            print(f"⚠️ 親ツイート取得失敗 ({tweet_id}): {e}")
            fetched_tweets[tweet_id] = None
        return fetched_tweets[tweet_id]

    # 古い順に処理
    for tweet in reversed(mentions.data):
        print(f"📩 リプライ発見: {tweet.text}")

        # リプライツリーの元ツイートを特定
        root_tweet_id = get_root_tweet_id(
            tweet,
            included_tweets=included_tweets,
            fetch_tweet=fetch_tweet,
        )
        own_tweet_text = None
        if root_tweet_id:
            own_tweet_text = find_tweet_text(root_tweet_id)
            if own_tweet_text:
                print(f"📝 リプライ先の自分のツイート: {own_tweet_text}")
            else:
                print(f"⚠️ リプライ先のツイートが履歴に見つかりません: {root_tweet_id}")

        # 会話履歴を取得
        author_id = tweet.author_id
        conversation_history = None
        if root_tweet_id and author_id:
            conversation_history = get_conversation_history(root_tweet_id, author_id)
        user_memory = load_user_memory(author_id) if author_id else None

        # 返信生成
        reply_text = client.generate_reply(
            tweet.text,
            own_tweet_text=own_tweet_text,
            conversation_history=conversation_history,
            user_memory=user_memory,
        )

        if reply_text:
            print(f"🤖 返信を生成: {reply_text[:30]}...")
            posted_id = client.post_tweet(reply_text, reply_id=tweet.id)
            if posted_id:
                save_last_id(tweet.id)
                if root_tweet_id and author_id:
                    add_exchange(root_tweet_id, author_id, tweet.text, reply_text)
                if author_id:
                    try:
                        updated_memory = client.generate_user_memory(
                            user_memory or "",
                            tweet.text,
                            reply_text,
                            own_tweet_text=own_tweet_text,
                        )
                        if updated_memory:
                            save_user_memory(author_id, updated_memory)
                    except Exception as e:
                        print(f"⚠️ ユーザーメモリ更新失敗 ({author_id}): {e}")
                print(f"✅ 返信成功: {posted_id}")
            time.sleep(5)


if __name__ == "__main__":
    main()
