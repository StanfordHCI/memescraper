import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE


class TheFunnyBeaverCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(TheFunnyBeaverCrawler, self).__init__(source='the_funny_beaver', *args, **kwargs)
        self.url = 'http://thefunnybeaver.com/page/{}/?s=memes'

    def _parse_html(self, html_content, post_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        article = soup.find("article", {"class": "post"})
        imgs = article.findAll("img")
        for i in imgs:
            url = i.attrs.get('src')
            img_class = i.attrs.get("class")
            if not len(img_class):
                continue
            img_id = None
            for c in img_class:
                if "wp-image" in c:
                    class_parts = c.split("-")
                    img_id = class_parts[len(class_parts) - 1]
            if img_id is None:
                continue
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
            response = requests.get(self.url.format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("article")
            for li in list_items:
                a = li.find("a")
                link = a.attrs.get("href")
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
                time.sleep(8)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
