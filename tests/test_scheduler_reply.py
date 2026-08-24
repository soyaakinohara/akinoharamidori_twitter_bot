import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.modules.setdefault("tweepy", types.SimpleNamespace(Client=object))

import scheduler


def tweet(tweet_id, author_id=None, text="", parent_id=None):
    references = None
    if parent_id is not None:
        references = [SimpleNamespace(type="replied_to", id=str(parent_id))]
    return SimpleNamespace(
        id=str(tweet_id),
        author_id=author_id,
        text=text,
        referenced_tweets=references,
    )


class FakeTwitter:
    def __init__(self, response, fetched_tweets):
        self.response = response
        self.fetched_tweets = fetched_tweets
        self.fetch_calls = []

    def get_users_mentions(self, *args, **kwargs):
        return self.response

    def get_tweet(self, tweet_id, **kwargs):
        self.fetch_calls.append((tweet_id, kwargs))
        return SimpleNamespace(data=self.fetched_tweets[tweet_id])


class FakeClient:
    def __init__(self, twitter):
        self.twitter = twitter
        self.env = {"REPLY_START_TIME": "2026-01-01T00:00:00Z"}
        self.reply_call = None
        self.memory_call = None

    def get_user_id(self):
        return "bot"

    def generate_reply(self, *args, **kwargs):
        self.reply_call = (args, kwargs)
        return "ボットの返信"

    def post_tweet(self, text, reply_id=None):
        return "201"

    def generate_user_memory(self, *args, **kwargs):
        self.memory_call = (args, kwargs)
        return "更新済みメモ"


class SchedulerReplyTests(unittest.TestCase):
    def test_nested_reply_uses_root_tweet_for_context_and_memory(self):
        root = tweet("100", text="example tweet")
        bot_reply = tweet("101", author_id="bot", text="ボットの返信", parent_id="100")
        user_reply = tweet(
            "102",
            author_id="user-A",
            text="続きの話をしよう",
            parent_id="101",
        )
        response = SimpleNamespace(
            data=[user_reply],
            includes={"tweets": [bot_reply]},
        )
        twitter = FakeTwitter(response, {"100": root})
        client = FakeClient(twitter)

        with patch.object(scheduler, "get_last_id", return_value="1"), \
                patch.object(scheduler, "save_last_id"), \
                patch.object(scheduler.time, "sleep"), \
                patch("tweet_history.find_tweet_text", return_value="example tweet"), \
                patch("reply_context.get_conversation_history", return_value="過去の会話"), \
                patch("reply_context.add_exchange") as add_exchange, \
                patch.object(scheduler, "load_user_memory", return_value="既存メモ"), \
                patch.object(scheduler, "save_user_memory") as save_memory:
            scheduler.run_reply_job(client)

        self.assertEqual(twitter.fetch_calls[0][0], "100")
        self.assertEqual(client.reply_call[1]["own_tweet_text"], "example tweet")
        self.assertEqual(client.reply_call[1]["conversation_history"], "過去の会話")
        self.assertEqual(client.reply_call[1]["user_memory"], "既存メモ")
        add_exchange.assert_called_once_with(
            "100", "user-A", "続きの話をしよう", "ボットの返信"
        )
        save_memory.assert_called_once_with("user-A", "更新済みメモ")


if __name__ == "__main__":
    unittest.main()
