import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class OnSizzleCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(OnSizzleCrawler, self).__init__(source='on_sizzle', *args, **kwargs)
        self.url = 'https://onsizzle.com/ajax/new_items{}'

    def get_feed(self, next_token=None):
        images = []
        if next_token is not None:
            page = '?since={}'.format(next_token)
        else:
            page = ''
        response = requests.get(self.url.format(page))
        next_token = None
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            container = soup.find("div", {"class": "container-item"})
            next_token = container.attrs.get('data-ext-next-token')
            imgs_html = soup.findAll('img')
            for i in imgs_html:
                url = i.attrs.get('src')
                if url is None:
                    continue
                href_parts = i.parent.attrs['href'].split('-')
                img_id = href_parts[len(href_parts) - 1]
                images.append({
                    "id": img_id,
                    "title": i.attrs.get('alt'),
                    "url": url
                })

        return images, next_token

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/on_sizzle/{}.jpg'.format(d['id']),
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
                if len(data):
                    pre_processed_data = self._pre_process_data(data[0])
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        next_page = 0
                        time.sleep(16)
                time.sleep(8)
                if next_page >= MAX_PAGE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
