import json
import os
import time

import requests

from crawlers.generic import BaseCrawler
from settings import TUMBLR_OAUTH_KEY, BEGIN_CRAWL_SINCE


class TumblrCrawler(BaseCrawler):

    def __init__(self, blogs, *args, **kwargs):
        super(TumblrCrawler, self).__init__(source='tumblr', *args, **kwargs)
        self.url = 'https://api.tumblr.com/v2/blog/{}/posts?api_key=' + TUMBLR_OAUTH_KEY
        self.blogs = blogs

    def get_feed(self, blog, offset=0):
        response = requests.get(self.url.format(blog) + '&offset={}'.format(offset))
        data = {}
        if response.status_code == 200:
            data = json.loads(response.content).get("response", {})

        return data

    def get_max_number_of_notes(self, blog):
        images = self.mongo_database.get_upvotes_by_source(self.source, blog)
        max_upvotes = [i['upvote_count'] for i in images if i['upvote_count'] is not None]
        return max(max_upvotes)

    def _pre_process_data(self, blog, data):
        results = []
        for post in data.get('posts', []):
            if post['type'] != 'photo':
                continue
            if not len(post.get("photos", [])):
                continue
            results.append(
                {
                    "id": post['id'],
                    "image_url": post['photos'][0]['original_size']['url'],
                    "file_name": 'data/tumblr/{}/{}.jpg'.format(blog, post['id']),
                    "source": self.source,
                    "created_at": post['timestamp'],
                    "child_source": post.get("blog_name"),
                    "post_url": post.get("post_url"),
                    'source_link': post.get("source_url"),
                    "comment_count": None,
                    "upvote_count": post.get("note_count")
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        offset = 0

        while self.running:
            try:
                for blog in self.blogs:
                    offset = 0
                    try:
                        max_notes = self.get_max_number_of_notes(blog)
                        self.mongo_database.update_source_followers(blog, max_likes=max_notes)
                    except Exception as e:
                        pass
                        # self._log_console("Failed to get max notes")
                    data = self.get_feed(blog, offset)
                    pre_processed_data = self._pre_process_data(blog, data)
                    offset += len(data.get("posts", []))
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                        offset = 0
                        time.sleep(2)
                        continue
                    time.sleep(16)
                    self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
