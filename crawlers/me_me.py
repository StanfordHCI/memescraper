import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class MeMeCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MeMeCrawler, self).__init__(source='me_me', *args, **kwargs)
        self.url = 'https://me.me/?s=new'
        self.alternative_sources = ["awwmemes"]

    def _parse_html(self, html_content, page=0):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        next_query = ''
        if page == 0:
            containers = soup.findAll("div", {"class": "item-container"})
            # pagination_container = soup.findAll("div", {"class": "container-item"})
            pagination_container = soup.findAll("div", {"class": "pagination-container"})
            if len(pagination_container):
                next_query = pagination_container[0].find("a").attrs.get("href", '')
        else:
            containers = soup.findAll("div", {"class": "grid-item"})
            pagination_container = soup.findAll("div", {"class": "container-item"})
            if len(pagination_container):
                next_query = "/?since={}".format(pagination_container[0].attrs.get("data-ext-next-token"))
        for c in containers:
            item = c.find("div")
            i = c.find_all("img")[1]
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            img_id = item.attrs.get("data-ext-id")
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url
            })
        return images, next_query

    def get_feed(self, page=0, next_query=''):
        images = []
        if page == 0:
            page_url = self.url
        else:
            page_url = "https://me.me/ajax/new_items?s=new&{}".format(next_query.strip("/?"))

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
                    "file_name": 'data/me_me/{}.jpg'.format(d['id']),
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
                if not inserted or oldest_timestamp < oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    next_page_query = ''
                    time.sleep(120)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
