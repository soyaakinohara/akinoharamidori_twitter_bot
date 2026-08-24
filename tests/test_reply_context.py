import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import reply_context


class ReplyContextTests(unittest.TestCase):
    def test_context_is_scoped_to_tweet_and_user(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context_file = Path(temp_dir) / "reply_context.json"
            with patch.object(reply_context, "CONTEXT_FILE", str(context_file)):
                reply_context.add_exchange(
                    "tweet-1", "user-A", "こんにちは", "こんにちは、君。"
                )
                reply_context.add_exchange(
                    "tweet-1", "user-B", "ちんちん", "……そういう日もあるね。"
                )

                user_a_history = reply_context.get_conversation_history("tweet-1", "user-A")
                user_b_history = reply_context.get_conversation_history("tweet-1", "user-B")
                other_tweet_history = reply_context.get_conversation_history("tweet-2", "user-A")

        self.assertIn("こんにちは", user_a_history)
        self.assertNotIn("ちんちん", user_a_history)
        self.assertIn("ちんちん", user_b_history)
        self.assertNotIn("こんにちは", user_b_history)
        self.assertEqual(other_tweet_history, "")


if __name__ == "__main__":
    unittest.main()
