import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class DumpADayCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(DumpADayCrawler, self).__init__(source='dump_a_day', *args, **kwargs)
        self.url = 'http://www.dumpaday.com/?s=memes'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.find("div", {"class": "entry"})
        imgs = main_content.findAll("img")
        for i in imgs:
            url = i.attrs.get('src')
            img_class = i.attrs.get("class", [])
            if not len(img_class):
                continue
            if "wp-image" not in img_class[2]:
                continue
            class_parts = img_class[2].split("-")
            img_id = class_parts[len(class_parts) - 1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": page_url,
                "post_id": i.attrs.get("data-frizzly-image-post-id")
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
        while status_code not in [404, 500]:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("http://www.dumpaday.com/page/{}/?s=memes".format(page))
            status_code = response.status_code
            if status_code != 200:
                continue
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("article", {"class": "post"})
            for li in list_items:
                link = li.find("a").attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
                    yield link

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
                    "page_url": d.get('page_url'),
                    "post_id": d.get('post_id'),
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
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        time.sleep(4)
                        break
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(120)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
