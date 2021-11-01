import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class IfunnyCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(IfunnyCrawler, self).__init__(source='ifunny', *args, **kwargs)
        self.url = 'https://ifunny.co/'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.find("div", {"class": "feed__list"})
        items = main_content.findAll("li", {"class": "stream__item"})
        next_token = None
        for li in items:
            i = li.find("img")
            if i is None or '.gif' in i.attrs.get('src'):
                continue
            a = li.find("a")
            url = i.attrs.get('src')
            if next_token is None:
                next_token = li.attrs.get("data-next")
            img_id_parts = a.attrs.get("href", '').split('/')
            img_id = img_id_parts[len(img_id_parts) - 1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": page_url
            })
        return images, next_token

    def get_feed(self, page_url):
        images = []
        next_token = None
        response = requests.get(page_url)
        if response.status_code == 200:
            images, next_token = self._parse_html(response.content, page_url)
        return images, next_token

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "page_url": d.get('page_url'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        next_token = ''
        while self.running:
            try:
                url = ''
                next_page += 1
                if next_page == 1:
                    url = self.url
                else:
                    url = 'https://ifunny.co/feeds/featured/{}?batch={}&mode=list'.format(next_token, next_page)
                data, next_token = self.get_feed(url)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                # time.sleep(360)
                time.sleep(4)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    time.sleep(32)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
