import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE


class TheChiveCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(TheChiveCrawler, self).__init__(source='the_chive', *args, **kwargs)
        self.url = 'http://thechive.com/category/humor/meme/'

    def _parse_html(self, html_content, post_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        figures = soup.findAll("figure")
        for f in figures:
            i = f.find("img")
            if i is None:
                continue
            url = i.attrs.get('src')
            img_id = f.attrs.get("data-attachment-id")
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "post_url": post_url
            })
        return images

    def get_feed(self, page_url):
        images = []
        response = requests.get(page_url)
        if response.status_code == 200:
            images = self._parse_html(response.content, page_url)
        return images

    def get_galleries(self):
        status_code = 200
        galleries = []
        page = 1
        while status_code != 404:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("http://thechive.com/category/humor/meme/page/{}".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("a", {"class": "card-img-link"})
            for li in list_items:
                link = li.attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
                    yield link
            status_code = response.status_code
            page += 1
            if page > MAX_PAGE:
                page = 1

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
        while self.running:
            try:
                galleries = self.get_galleries()
                for g in galleries:
                    data = self.get_feed(g)
                    pre_processed_data = self._pre_process_data(data)
                    self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
