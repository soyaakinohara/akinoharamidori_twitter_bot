import os
import re
import tempfile
from pathlib import Path

USER_MEMORY_DIR = Path("usermemory")
MAX_MEMORY_CHARS = 4000
SAFE_USER_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _memory_path(author_id):
    user_id = str(author_id)
    if not user_id or not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("author_id は安全なファイル名に使える文字だけで指定してください")
    return Path(USER_MEMORY_DIR) / f"{user_id}.md"


def load_user_memory(author_id):
    """ユーザーごとの永続メモリを読み込む。未作成・読込失敗時は空文字を返す。"""
    path = _memory_path(author_id)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def save_user_memory(author_id, memory):
    """ユーザーごとの永続メモリをMarkdownとして安全に置き換える。"""
    path = _memory_path(author_id)
    text = str(memory).strip()[:MAX_MEMORY_CHARS].rstrip()
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(text)
            temporary_path = temporary_file.name
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
