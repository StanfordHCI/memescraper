import tweepy
import settings
import time

from crawlers.generic import BaseCrawler

auth = tweepy.OAuthHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)
auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)

api = tweepy.API(auth)


class TwitterCrawler(BaseCrawler):

    def __init__(self, handles, *args, **kwargs):
        super(TwitterCrawler, self).__init__(source='twitter', *args, **kwargs)
        self.url = 'https://www.twitter.com/{}/'
        self.handles = handles

    def get_feed(self, handle):
        tweets = api.user_timeline(handle, count=256, include_rts=True)
        return tweets

    def _pre_process_data(self, handle, data):
        results = []
        for e in data:
            try:
                create_at_t = int(e.created_at.strftime("%s"))
                if create_at_t >= settings.BEGIN_CRAWL_SINCE:
                    for m in e._json.get("entities", {}).get("media", []):
                        if m['type'] == 'photo':
                            results.append(
                                {
                                    "id": m['id_str'],
                                    "upvote_count": e.favorite_count,
                                    "image_url": m.get("media_url"),
                                    "file_name": 'data/{}/{}/{}.jpg'.format(self.source, handle, m['id_str']),
                                    "source": self.source,
                                    "created_at": create_at_t,
                                    "reshared": e.retweeted,
                                    "child_source": handle,
                                    "shares_count": e.retweet_count
                                    # "comment_count": e['node'].get("edge_media_to_comment", {}).get("count")
                                }
                            )
            except Exception as e:
                print("twitter {} failed to preprocess data".format(handle))
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                for page in self.handles:
                    try:
                        data = self.get_feed(page['screen_name'])
                        try:
                            self.mongo_database.update_twitter_activity(page['screen_name'], time.time())
                        except Exception as e:
                            pass
                        pre_processed_data = self._pre_process_data(page['screen_name'], data)
                        self.process_data(pre_processed_data)
                        self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
                    except Exception as e:
                        pass
                    time.sleep(8)
                time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
