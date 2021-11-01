import time

import praw
import threading
import settings
from crawlers.generic import BaseCrawler


reddit_praw = praw.Reddit(client_id=settings.REDDIT_CLIENT_ID, client_secret=settings.REDDIT_CLIENT_SECRET,
                          password=settings.REDDIT_PASSWORD,
                          user_agent='memeID-C7', username=settings.REDDIT_USERNAME)
PAGE_SIZE = 100


def r_get_feed_new(sr, params):
    return sr.new(limit=PAGE_SIZE, params=params)


def r_get_submission_comments(url):
    return reddit_praw.submission(url=url).comments


class RedditCrawler(BaseCrawler):
    sub_reddits = []

    def __init__(self, sub_reddits, *args, **kwargs):
        super(RedditCrawler, self).__init__(source='reddit', *args, **kwargs)
        self.url = 'https://reddit.com'
        self.sub_reddits = sub_reddits

    def get_feed(self, sub_reddit, params, page_size=PAGE_SIZE):
        return sub_reddit.new(limit=page_size, params=params)

    def get_subscribers(self, sub_reddit):
        return sub_reddit.subscribers

    def _pre_process_data(self, subreddit, data):
        results = []
        last = None
        for d in data:
            if d.created_utc >= settings.BEGIN_CRAWL_SINCE:
                results.append(
                    {
                        "id": d.id,
                        "upvote_count": d.ups,
                        "score": d.score,
                        "comment_count": d.num_comments,
                        "image_url": d.url,
                        "file_name": 'data/reddit/{}.jpg'.format(d.id),
                        "source": self.source,
                        "url": d.shortlink,
                        "created_at": d.created_utc,
                        "child_source": "r/{}".format(d.subreddit.display_name).lower(),
                        "subreddit_id": d.subreddit_id,
                        "title": d.title,
                        "is_video": d.is_video
                    }
                )
                last = d
        return results, last

    def _fetch_subscribers(self):
        for sub_reddit in self.sub_reddits:
            sr = reddit_praw.subreddit(sub_reddit)
            try:
                s_name = sub_reddit
                if not sub_reddit.startswith('r/'):
                    s_name = 'r/' + sub_reddit
                self.mongo_database.update_source_followers(s_name, self.get_subscribers(sr))
            except:
                self._log_console("Failed to fetch subscribers...")

    def run(self):

        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        params = {}
        threading.Thread(target=self._fetch_subscribers).start()
        while self.running:
            try:
                for sub_reddit in self.sub_reddits:
                    params = {}
                    sr = reddit_praw.subreddit(sub_reddit)
                    data = self.get_feed(sr, params)
                    pre_processed_data, last = self._pre_process_data(data=data, subreddit=sub_reddit)
                    if last is not None:
                        params.update({"after": last.name})
                        if 'count' not in params:
                            params['count'] = 0
                        params['count'] += 100
                    else:
                        if 'count' not in params:
                            params['count'] = 0
                        params['count'] += 100
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    time.sleep(8)
                    self._log_console("Iteration ended ...")
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
