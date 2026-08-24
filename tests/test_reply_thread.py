import unittest
from types import SimpleNamespace

from reply_thread import get_root_tweet_id


def tweet(tweet_id, parent_id=None):
    references = None
    if parent_id is not None:
        references = [SimpleNamespace(type="replied_to", id=str(parent_id))]
    return SimpleNamespace(id=str(tweet_id), referenced_tweets=references)


class ReplyThreadTests(unittest.TestCase):
    def test_resolves_root_from_included_tweets(self):
        root = tweet("100")
        bot_reply = tweet("101", parent_id="100")
        user_reply = tweet("102", parent_id="101")

        resolved = get_root_tweet_id(
            user_reply,
            included_tweets={"101": bot_reply, "100": root},
        )

        self.assertEqual(resolved, "100")

    def test_fetches_missing_parent_when_resolving_root(self):
        root = tweet("100")
        bot_reply = tweet("101", parent_id="100")
        user_reply = tweet("102", parent_id="101")
        fetched_ids = []

        def fetch_tweet(tweet_id):
            fetched_ids.append(tweet_id)
            return root if tweet_id == "100" else None

        resolved = get_root_tweet_id(
            user_reply,
            included_tweets={"101": bot_reply},
            fetch_tweet=fetch_tweet,
        )

        self.assertEqual(resolved, "100")
        self.assertEqual(fetched_ids, ["100"])


if __name__ == "__main__":
    unittest.main()
