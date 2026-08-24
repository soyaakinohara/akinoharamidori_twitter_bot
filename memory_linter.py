from datetime import datetime, timedelta, timezone
from pathlib import Path

from user_memory import USER_MEMORY_DIR, load_user_memory, save_user_memory

LINT_STATE_FILE = Path("last_memory_lint.txt")
LINT_INTERVAL = timedelta(days=7)


def _as_utc(value):
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_last_lint_time():
    try:
        value = LINT_STATE_FILE.read_text(encoding="utf-8").strip()
        last_run = datetime.fromisoformat(value)
        return _as_utc(last_run)
    except (OSError, TypeError, ValueError):
        return None


def is_lint_due(now=None):
    """前回のlintから7日以上経過しているか確認する。"""
    last_run = _load_last_lint_time()
    if last_run is None:
        return True
    return _as_utc(now) - last_run >= LINT_INTERVAL


def mark_lint_run(run_at=None):
    """lint実行時刻をUTCで保存する。"""
    run_at = _as_utc(run_at)
    LINT_STATE_FILE.write_text(run_at.isoformat(), encoding="utf-8")


def _memory_user_ids():
    directory = Path(USER_MEMORY_DIR)
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.md") if path.is_file())


def lint_all_memories(client, now=None):
    """全ユーザーメモリを週次lintし、実行結果を返す。"""
    run_at = _as_utc(now)
    if not is_lint_due(run_at):
        return {"ran": False, "checked": 0, "changed": 0, "failed": 0}

    checked = 0
    changed = 0
    failed = 0
    for user_id in _memory_user_ids():
        original = load_user_memory(user_id)
        if not original.strip():
            continue
        checked += 1
        try:
            linted = client.lint_user_memory(original)
            # 空レスポンスで既存の記憶を消さない。
            if linted and linted != original:
                save_user_memory(user_id, linted)
                changed += 1
        except Exception as error:
            failed += 1
            print(f"⚠️ ユーザーメモリlint失敗 ({user_id}): {error}")

    mark_lint_run(run_at)
    return {"ran": True, "checked": checked, "changed": changed, "failed": failed}
