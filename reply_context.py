import json
import os

CONTEXT_FILE = "reply_context.json"
MAX_CONTEXT = 10


def load_context():
    if not os.path.exists(CONTEXT_FILE):
        return {}
    try:
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_context(context):
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)


def get_conversation_key(own_tweet_id, author_id):
    """自分のツイートID + 相手のユーザーID で会話を識別"""
    return f"{own_tweet_id}_{author_id}"


def add_exchange(own_tweet_id, author_id, user_text, bot_reply_text):
    context = load_context()
    key = get_conversation_key(own_tweet_id, author_id)
    if key not in context:
        context[key] = []
    context[key].append({
        "user": user_text,
        "bot": bot_reply_text
    })
    if len(context[key]) > MAX_CONTEXT:
        context[key] = context[key][-MAX_CONTEXT:]
    save_context(context)


def get_conversation_history(own_tweet_id, author_id):
    context = load_context()
    key = get_conversation_key(own_tweet_id, author_id)
    exchanges = context.get(key, [])
    lines = []
    for ex in exchanges:
        lines.append(f"- 相手: {ex['user']}")
        lines.append(f"- 緑: {ex['bot']}")
    return "\n".join(lines)
