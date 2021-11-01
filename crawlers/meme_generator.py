import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class MemeGeneratorCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MemeGeneratorCrawler, self).__init__(source='meme_generator', *args, **kwargs)
        self.url = 'https://memegenerator.net/images/new/today{}'

    def get_feed(self, next_page=None):
        images = []
        if next_page is not None and next_page:
            page = '/{}'.format(next_page)
        else:
            page = ''
        response = requests.get(self.url.format(page))
        seen_imgs = []
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            container = soup.find("div", {"class": "tabs-content"})
            divs_html = container.findAll('div', {"class": "img"})
            for d in divs_html:
                i = d.find("img")
                url = i.attrs.get('src')
                if url is None:
                    continue
                href_parts = i.parent.parent.parent.attrs['href'].split('/')
                img_id = href_parts[2]
                if img_id in seen_imgs:
                    continue
                seen_imgs.append(img_id)
                images.append({
                    "id": img_id,
                    "title": i.attrs.get('alt'),
                    "url": url
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
                    "file_name": 'data/meme_generator/{}.jpg'.format(d['id']),
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
                    pre_processed_data = self._pre_process_data(data)
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        next_page = 0
                        time.sleep(8)
                time.sleep(4)
                if next_page >= MAX_PAGE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
