import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class CleanMemesCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(CleanMemesCrawler, self).__init__(source='clean_memes', *args, **kwargs)
        self.url = 'https://cleanmemes.com/'

    def get_feed(self, page=1):
        images = []
        page_url = self.url
        if page > 1:
            page_url = '{}/page/{}/'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('article', {"class": "post"})
            for a in posts:
                try:
                    imgs = a.findAll("img")
                    t = a.find("time", {"class": "entry-date"})
                    for i in imgs:
                        img_id = [c for c in i.attrs.get('class', []) if c.startswith('wp-image-')][0].strip(
                            'wp-image-')
                        if img_id is None:
                            continue
                        images.append({
                            "id": img_id,
                            "title": i.attrs.get('alt'),
                            "url": i.attrs.get('src'),
                            "created_at": time.mktime(
                                time.strptime(t.attrs.get("datetime"), '%Y-%m-%dT%H:%M:%S-04:00')) - (
                                                  UTC_HOUR_DIFF - 4) * 3600
                        })
                except Exception as e:
                    print(e)

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
        while self.running:
            try:
                data = self.get_feed(1)

                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(32)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    time.sleep(180)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
