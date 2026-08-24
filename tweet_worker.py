import os
import sys
from datetime import datetime
from midori_client import MidoriClient
from tweet_history import add_tweet, get_recent_texts

# --- 秋ノ原緑ボット 自動ツイート部隊 ---

LAST_TWEET_FILE = "last_tweet_id.txt"


def get_last_tweet_id():
    if os.path.exists(LAST_TWEET_FILE):
        with open(LAST_TWEET_FILE, "r") as f:
            return f.read().strip()
    return None


def save_last_tweet_id(tweet_id):
    with open(LAST_TWEET_FILE, "w") as f:
        f.write(str(tweet_id))


def is_sleep_hours():
    """22:00〜07:00は休眠"""
    now = datetime.now().hour
    return now >= 22 or now < 7


def main():
    if is_sleep_hours():
        print("🌙 休眠時間帯なのでツイートしません。")
        sys.exit(0)

    client = MidoriClient()

    # 直近のツイートを文脈として取得
    context = get_recent_texts(count=5)

    print("📝 ツイート文を生成中...")
    tweet_text = client.generate_tweet(context=context)

    if not tweet_text:
        print("❌ ツイート文の生成に失敗しました。")
        sys.exit(1)

    print(f"🐦 ツイート: {tweet_text}")

    tweet_id = client.post_tweet(tweet_text)
    if tweet_id:
        save_last_tweet_id(tweet_id)
        add_tweet(tweet_id, tweet_text)
        print(f"✅ 投稿成功: {tweet_id}")
    else:
        print("❌ 投稿に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()
