import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE

PAGE_SIZE = 256


class FreshSubstanceCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):
        super(FreshSubstanceCrawler, self).__init__(source='fresh_substance', *args, **kwargs)
        self.url = 'https://funsubstance.com/fun/list/?category=fresh'
        self.timeout = 16

    def get_feed(self, next_id=None):
        images = []
        page_url = self.url
        if next_id is not None:
            page_url = '{}&next={}'.format(self.url, next_id)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(json.loads(response.content).get("posts", ''), 'html.parser')
            posts = soup.findAll("div", {"class": 'post'})
            for p in posts:
                i = p.find("img")
                images.append({
                    "id": p.attrs.get("data-id"),
                    "title": i.attrs.get("alt"),
                    "url": i.attrs.get('src'),
                })
                next_id = p.attrs.get("data-id")

        return images, next_id

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get("url"),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "created_at": d.get('created')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_id = None
        while self.running:
            try:
                data, next_id = self.get_feed(next_id)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_id = None
                time.sleep(30)
                self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
