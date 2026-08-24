import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import user_memory


class UserMemoryTests(unittest.TestCase):
    def test_saves_memory_per_user_as_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(user_memory, "USER_MEMORY_DIR", Path(temp_dir)):
                user_memory.save_user_memory("user-123", "## 興味\n- 廃墟の写真")

                memory = user_memory.load_user_memory("user-123")

            self.assertEqual(memory, "## 興味\n- 廃墟の写真")
            self.assertTrue((Path(temp_dir) / "user-123.md").is_file())

    def test_user_id_is_restricted_to_a_safe_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(user_memory, "USER_MEMORY_DIR", Path(temp_dir)):
                with self.assertRaises(ValueError):
                    user_memory.save_user_memory("../other-user", "秘密")


if __name__ == "__main__":
    unittest.main()
