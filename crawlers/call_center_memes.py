import time

import requests
from bs4 import BeautifulSoup
import hashlib

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class CallCenterMemesCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(CallCenterMemesCrawler, self).__init__(source='call_center_memes', *args, **kwargs)
        self.url = 'http://www.callcentermemes.com/category/meme-images/'

    def get_feed(self, page=0):
        images = []
        page_url = self.url
        if page > 0:
            page_url = '{}page/{}'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.findAll("article", {"class": "post"})
            for a in articles:
                i = a.find('img')
                t = a.find('time')
                images.append({
                    "id": a.attrs.get('id').strip('post-'),
                    "title": i.attrs.get('alt'),
                    "url": i.attrs.get('src'),
                    "created_at": time.mktime(
                        time.strptime(t.attrs.get("datetime"), '%Y-%m-%dT%H:%M:%S+00:00')) - 3600 * UTC_HOUR_DIFF
                })

        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "created_at": d.get('created_at')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        while self.running:
            try:
                data = self.get_feed(next_page)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
