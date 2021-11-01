import time

import requests
from bs4 import BeautifulSoup
import hashlib

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


# incomplete

class MegaMemeCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MegaMemeCrawler, self).__init__(source='mega_meme', *args, **kwargs)
        self.url = 'https://megamemes.lol/'

    def get_feed(self, page=0):
        images = []
        page_url = self.url
        if page > 0:
            page_url = '{}page/{}'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            article = soup.find("article", {"class": "post"})
            i = article.find('img')
            m = hashlib.sha256(i.attrs.get('src'))
            images.append({
                "id": m.hexdigest(),
                "title": i.attrs.get('alt'),
                "url": i.attrs.get('src')
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
                    "source": self.source
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
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
