import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import memory_linter
import user_memory


class MemoryLinterScheduleTests(unittest.TestCase):
    def test_lint_is_due_when_state_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "last_memory_lint.txt"
            with patch.object(memory_linter, "LINT_STATE_FILE", state_file):
                self.assertTrue(
                    memory_linter.is_lint_due(
                        now=datetime(2026, 8, 25, tzinfo=timezone.utc)
                    )
                )

    def test_lint_is_not_due_until_a_week_has_passed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "last_memory_lint.txt"
            state_file.write_text("2026-08-20T12:00:00+00:00", encoding="utf-8")
            with patch.object(memory_linter, "LINT_STATE_FILE", state_file):
                self.assertFalse(
                    memory_linter.is_lint_due(
                        now=datetime(2026, 8, 25, tzinfo=timezone.utc)
                    )
                )
                self.assertTrue(
                    memory_linter.is_lint_due(
                        now=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
                    )
                )

    def test_mark_lint_run_writes_utc_timestamp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "last_memory_lint.txt"
            run_at = datetime(2026, 8, 25, 12, 34, tzinfo=timezone.utc)
            with patch.object(memory_linter, "LINT_STATE_FILE", state_file):
                memory_linter.mark_lint_run(run_at)

                self.assertEqual(
                    state_file.read_text(encoding="utf-8"),
                    "2026-08-25T12:34:00+00:00",
                )

    def test_lints_files_and_does_not_delete_on_empty_llm_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_dir = Path(temp_dir) / "usermemory"
            memory_dir.mkdir()
            (memory_dir / "user-1.md").write_text(
                "## 興味\n- 廃墟の写真が好き", encoding="utf-8"
            )
            (memory_dir / "user-2.md").write_text(
                "## 興味\n- 古い駅が好き", encoding="utf-8"
            )
            state_file = Path(temp_dir) / "last_memory_lint.txt"
            client = Mock()
            client.lint_user_memory.side_effect = [
                "## 興味\n- 廃墟の写真が好き\n- 写真を撮る",
                "",
            ]

            with patch.object(memory_linter, "USER_MEMORY_DIR", memory_dir), \
                    patch.object(user_memory, "USER_MEMORY_DIR", memory_dir), \
                    patch.object(memory_linter, "LINT_STATE_FILE", state_file):
                result = memory_linter.lint_all_memories(
                    client,
                    now=datetime(2026, 8, 25, tzinfo=timezone.utc),
                )

            self.assertEqual(result, {"ran": True, "checked": 2, "changed": 1, "failed": 0})
            self.assertIn("写真を撮る", (memory_dir / "user-1.md").read_text(encoding="utf-8"))
            self.assertEqual(
                (memory_dir / "user-2.md").read_text(encoding="utf-8"),
                "## 興味\n- 古い駅が好き",
            )
            self.assertEqual(client.lint_user_memory.call_count, 2)


if __name__ == "__main__":
    unittest.main()
