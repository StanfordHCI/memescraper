import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class PutMeLikeCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(PutMeLikeCrawler, self).__init__(source='put_me_like', *args, **kwargs)
        self.url = 'https://putmelike.com/category/memes'

    def get_feed(self, page=1):
        images = []
        page_url = self.url
        if page > 1:
            page_url = '{}/page/{}/'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('article', {"class": "post"})
            for p in posts:
                try:
                    i = p.find("img")
                    t = p.find('time', {"class": "entry-date"})
                    images.append({
                        "id": p.attrs.get('id').strip('post-'),
                        "title": i.attrs.get('alt'),
                        "url": i.attrs.get('data-src', i.attrs.get('src')),
                        "created_at": time.mktime(
                            time.strptime(t.attrs.get('datetime'), '%Y-%m-%dT%H:%M:%S+03:00')) - (
                                                  3 + UTC_HOUR_DIFF) * 3600
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
        next_page = 0
        while self.running:
            try:
                next_page += 1
                data = self.get_feed(next_page)

                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    if next_page == 1:
                        time.sleep(360)
                    next_page = 0
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
