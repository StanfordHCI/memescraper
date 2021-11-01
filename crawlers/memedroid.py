import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class MemedroidCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MemedroidCrawler, self).__init__(source='memedroid', *args, **kwargs)
        self.url = 'https://www.memedroid.com/memes/latest'

    def _parse_html(self, html_content, page=0):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        next_query = ''
        containers = soup.findAll("article", {"class": "gallery-item"})
        pagination_container = soup.findAll("nav", {"class": "hidden"})
        # nav.hidden /memes/latest/1528398006
        if len(pagination_container):
            next_query = pagination_container[0].find("a").attrs.get("href", '')
        for c in containers:
            item = c.find("time")
            i = c.find_all("img")[0]
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            images.append({
                "id": c.attrs.get('id', '').strip("article-item-"),
                "title": i.attrs.get('alt'),
                "url": url,
                "time": time.mktime(time.strptime(item.attrs.get("datetime"), '%Y-%m-%dT%H:%M:%S')) - 10800
            })
        return images, next_query

    def get_feed(self, page=0, next_query=''):
        images = []
        if page == 0:
            page_url = self.url
        else:
            page_url = "https://www.memedroid.com{}".format(next_query)

        response = requests.get(page_url)
        if response.status_code == 200:
            images, next_query = self._parse_html(response.content, page=page)

        return images, next_query

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
        next_page_query = ''
        while self.running:
            try:
                data, next_page_query = self.get_feed(next_page, next_page_query)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(8)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    time.sleep(16)
                    next_page_query = ''
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
