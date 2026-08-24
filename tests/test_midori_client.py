import unittest
import sys
import types
from unittest.mock import Mock

# Clientの初期化を行わない単体テストなので、外部APIクライアントだけ差し替える。
sys.modules.setdefault("tweepy", types.SimpleNamespace(Client=object))

from midori_client import MidoriClient


class MidoriClientTests(unittest.TestCase):
    def setUp(self):
        self.client = object.__new__(MidoriClient)
        self.client._call_llm = Mock(return_value="## 会話傾向\n- 廃墟の写真が好き")

    def test_generate_reply_includes_user_memory(self):
        reply = self.client.generate_reply(
            "この前の話、覚えてる？",
            own_tweet_text="example tweet",
            conversation_history="- 相手: こんにちは\n- 緑: うん、こんにちは。",
            user_memory="## 興味\n- 廃墟の写真が好き",
        )

        self.assertEqual(reply, "## 会話傾向 - 廃墟の写真が好き")
        messages = self.client._call_llm.call_args.args[0]
        self.assertIn("ユーザーについての永続メモリ", messages[1]["content"])
        self.assertIn("廃墟の写真が好き", messages[1]["content"])

    def test_generate_user_memory_summarizes_new_exchange(self):
        memory = self.client.generate_user_memory(
            existing_memory="## 興味\n- 廃墟の写真が好き",
            user_text="最近は古い駅の写真を撮ってる",
            bot_reply_text="古い駅って、時間が止まったみたいでいいね。",
            own_tweet_text="廃駅を見つけた話",
        )

        self.assertIn("廃墟の写真が好き", memory)
        messages = self.client._call_llm.call_args.args[0]
        self.assertIn("ユーザー記憶を整理", messages[0]["content"])
        self.assertIn("古い駅の写真", messages[1]["content"])

    def test_lint_user_memory_removes_only_obviously_useless_information(self):
        self.client._call_llm = Mock(return_value="## 興味\n- 廃墟の写真が好き")

        linted = self.client.lint_user_memory("## 興味\n- 廃墟の写真が好き\n- テスト時の一時的な挨拶")

        self.assertEqual(linted, "## 興味\n- 廃墟の写真が好き")
        messages = self.client._call_llm.call_args.args[0]
        self.assertIn("明らかに無駄", messages[0]["content"])
        self.assertIn("テスト時の一時的な挨拶", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
