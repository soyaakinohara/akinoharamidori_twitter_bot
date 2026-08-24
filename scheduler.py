import time
import logging
from datetime import datetime, timedelta

from midori_client import MidoriClient
from tweet_worker import save_last_tweet_id, is_sleep_hours
from reply_worker import get_last_id, save_last_id
from reply_thread import get_included_tweets, get_root_tweet_id
from user_memory import load_user_memory, save_user_memory
from memory_linter import lint_all_memories

# --- 秋ノ原緑ボット 統合スケジューラー ---
# ・22:00〜07:00は休眠
# ・2時間ごとに自動ツイート
# ・ツイート後10分にリプライ確認

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s"
)
logger = logging.getLogger("midori-scheduler")

TWEET_INTERVAL_HOURS = 2
REPLY_DELAY_MINUTES = 10


def wait_until(target):
    """target時刻までスリープ"""
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            break
        sleep_sec = min(remaining, 60)
        logger.info(f"⏳ 次の実行まで {int(remaining)}秒...")
        time.sleep(sleep_sec)


def run_tweet_job(client):
    """自動ツイートジョブ"""
    logger.info("📝 自動ツイートジョブ開始")

    from tweet_history import get_recent_texts, add_tweet
    context = get_recent_texts(count=5)

    tweet_text = client.generate_tweet(context=context)
    if not tweet_text:
        logger.error("❌ ツイート文生成失敗")
        return None

    logger.info(f"🐦 ツイート: {tweet_text}")
    tweet_id = client.post_tweet(tweet_text)
    if tweet_id:
        save_last_tweet_id(tweet_id)
        add_tweet(tweet_id, tweet_text)
        logger.info(f"✅ 投稿成功: {tweet_id}")
    else:
        logger.error("❌ 投稿失敗")
    return tweet_id


def run_memory_lint_job(client):
    """週次のユーザーメモリ整理ジョブ"""
    result = lint_all_memories(client)
    if result["ran"]:
        logger.info(
            "🧹 ユーザーメモリlint完了: %d件確認、%d件更新、%d件失敗",
            result["checked"],
            result["changed"],
            result["failed"],
        )
    return result


def run_reply_job(client):
    """リプライ返信ジョブ"""
    logger.info("💬 リプライ確認ジョブ開始")

    from datetime import datetime, timedelta, timezone
    from tweet_history import find_tweet_text
    from reply_context import add_exchange, get_conversation_history

    user_id = client.get_user_id()
    since_id = get_last_id()
    start_time = client.env.get("REPLY_START_TIME")
    if not start_time:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    tweet_fields = ["created_at", "referenced_tweets"]
    expansions = ["author_id", "referenced_tweets.id"]

    try:
        if since_id:
            mentions = client.twitter.get_users_mentions(
                user_id,
                since_id=since_id,
                start_time=start_time,
                expansions=expansions,
                tweet_fields=tweet_fields
            )
        else:
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
                logger.info(f"📌 初回実行：最新メンションID {latest_id} を記録しました。次回から返信します。")
            else:
                logger.info("📭 新着リプライはありません。")
            return
    except Exception as e:
        logger.error(f"❌ メンション取得エラー: {e}")
        return

    if not mentions.data:
        logger.info("📭 新着リプライはありません。")
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
            logger.warning("⚠️ 親ツイート取得失敗 (%s): %s", tweet_id, e)
            fetched_tweets[tweet_id] = None
        return fetched_tweets[tweet_id]

    for tweet in reversed(mentions.data):
        logger.info(f"📩 リプライ: {tweet.text}")

        root_tweet_id = get_root_tweet_id(
            tweet,
            included_tweets=included_tweets,
            fetch_tweet=fetch_tweet,
        )
        own_tweet_text = find_tweet_text(root_tweet_id) if root_tweet_id else None
        author_id = tweet.author_id
        conversation_history = None
        if root_tweet_id and author_id:
            conversation_history = get_conversation_history(root_tweet_id, author_id)
        user_memory = load_user_memory(author_id) if author_id else None

        reply_text = client.generate_reply(
            tweet.text,
            own_tweet_text=own_tweet_text,
            conversation_history=conversation_history,
            user_memory=user_memory,
        )

        if reply_text:
            logger.info(f"🤖 返信: {reply_text[:30]}...")
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
                        logger.warning("⚠️ ユーザーメモリ更新失敗 (%s): %s", author_id, e)
                logger.info(f"✅ 返信成功: {posted_id}")
            time.sleep(5)


def main():
    client = MidoriClient()

    while True:
        if is_sleep_hours():
            logger.info("🌙 休眠時間帯です。07:00まで待機します。")
            now = datetime.now()
            wakeup = now.replace(hour=7, minute=0, second=0, microsecond=0)
            if now.hour >= 22:
                wakeup += timedelta(days=1)
            wait_until(wakeup)
            continue

        run_memory_lint_job(client)
        tweet_id = run_tweet_job(client)

        if tweet_id:
            logger.info(f"⏰ {REPLY_DELAY_MINUTES}分後にリプライ確認します")
            time.sleep(REPLY_DELAY_MINUTES * 60)
            run_reply_job(client)

        logger.info(f"⏳ 次のツイートまで{TWEET_INTERVAL_HOURS}時間待機します")
        time.sleep(TWEET_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()
