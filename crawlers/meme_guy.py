import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class MemeGuyCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MemeGuyCrawler, self).__init__(source='meme_guy', *args, **kwargs)
        self.url = 'https://memeguy.com/search/meme/{}/newest'

    def _parse_html(self, html_content):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        items = soup.findAll("li", {"class": "span3"})
        for li in items:
            a = li.find("a")
            i = li.find("img")
            img_id_parts = a.attrs.get('href').split("/")
            images.append({
                "id": img_id_parts[2],
                "title": i.attrs.get('alt'),
                "url": "https://memeguy.com{}".format(i.attrs.get('src'))
            })
        return images

    def get_feed(self, page=0):
        images = []
        response = requests.get(self.url.format(page))
        if response.status_code == 200:
            images = self._parse_html(response.content)

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
                next_page += 1
                data = self.get_feed(next_page)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(8)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    time.sleep(16)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
