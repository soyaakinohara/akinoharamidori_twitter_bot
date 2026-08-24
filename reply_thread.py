def get_referenced_tweet_id(tweet):
    """リプライ先のツイートIDを取得する。"""
    for reference in getattr(tweet, "referenced_tweets", None) or []:
        if getattr(reference, "type", None) == "replied_to":
            return str(reference.id)
    return None


def get_included_tweets(response):
    """APIレスポンスに展開されたツイートをIDで引ける辞書にする。"""
    includes = getattr(response, "includes", None) or {}
    tweets = includes.get("tweets", []) if hasattr(includes, "get") else []
    return {str(tweet.id): tweet for tweet in tweets}


def get_root_tweet_id(tweet, included_tweets=None, fetch_tweet=None):
    """返信ツリーをたどり、最上流のリプライ先IDを返す。

    ``included_tweets`` にない親は ``fetch_tweet`` で取得する。取得できない
    場合は、最後に確認できたリプライ先IDを返して処理を継続する。
    """
    included_tweets = included_tweets or {}
    current_tweet = tweet
    root_id = None
    visited_ids = set()

    while current_tweet is not None:
        parent_id = get_referenced_tweet_id(current_tweet)
        if parent_id is None:
            break

        root_id = parent_id
        if parent_id in visited_ids:
            break
        visited_ids.add(parent_id)

        current_tweet = included_tweets.get(parent_id)
        if current_tweet is None and fetch_tweet is not None:
            current_tweet = fetch_tweet(parent_id)

    return root_id
