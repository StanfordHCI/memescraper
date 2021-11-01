import json
import time

import requests
from bs4 import BeautifulSoup
import hashlib

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class Pr0grammCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(Pr0grammCrawler, self).__init__(source='pr0gramm', *args, **kwargs)
        self.url = 'https://pr0gramm.com'

    def get_feed(self, after=None):
        images = []
        page_url = "https://pr0gramm.com/api/items/get?flags=1"
        if after is not None:
            page_url = '{}&older={}'.format(page_url, after)
        response = requests.get(page_url)
        if response.status_code == 200:
            for x in json.loads(response.content).get('items'):
                images.append(x)

        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            if d.get('audio'):
                continue
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": "https://img.pr0gramm.com/{}".format(d.get('image')),
                    "upvote_count": d.get("up", 0),
                    "downvote_count": d.get("down", 0),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "created_at": d.get('created')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        after = None
        while self.running:
            try:
                data = self.get_feed(after)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(8)
                if len(pre_processed_data):
                    after = pre_processed_data[len(pre_processed_data) - 1].get("id")
                else:
                    after = None
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    after = 0

            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
