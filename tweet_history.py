import json
import os
from datetime import datetime, timezone

HISTORY_FILE = "tweet_history.json"
MAX_HISTORY = 50


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_tweet(tweet_id, text):
    history = load_history()
    history.append({
        "id": str(tweet_id),
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    # 古いものを削除
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    save_history(history)


def get_recent_texts(count=5):
    history = load_history()
    texts = [f"- {h['text']}" for h in history[-count:]]
    return "\n".join(texts)


def find_tweet_text(tweet_id):
    history = load_history()
    for h in history:
        if h["id"] == str(tweet_id):
            return h["text"]
    return None
