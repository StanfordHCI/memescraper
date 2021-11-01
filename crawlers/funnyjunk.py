import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class FunnyJunkCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(FunnyJunkCrawler, self).__init__(source='funny_junk', *args, **kwargs)
        self.url = 'https://funnyjunk.com/funnycontent/fpSort/frontNew24h{}'

    def get_feed(self, page=0):
        images = []
        if page > 0:
            page = '/{}'.format(page)
        else:
            page = ''
        response = requests.get(self.url.format(page))
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            imgs_html = soup.findAll("img")
            for i in imgs_html:
                if 'hdgifs' in i.attrs.get('data-original'):
                    continue
                if i.attrs.get('data-original')[:2] == '//':
                    url = 'https:' + i.attrs.get('data-original')
                else:
                    url = i.attrs.get('data-original')
                url_parts = i.attrs.get('data-original').split('/')
                img_id = url_parts[len(url_parts) - 1].split('.')[0]
                images.append({
                    "id": img_id,
                    "title": i.attrs.get('alt'),
                    "url": url.replace('thumbnails_160x160/pictures', 'pictures').replace('thumbnails/pictures',
                                                                                          'pictures')
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
                    "file_name": 'data/funny_junk/{}.jpg'.format(d['id']),
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        # self._register_signals()
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
