import time
import uuid

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class ImgLulzCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(ImgLulzCrawler, self).__init__(source='img_lulz', *args, **kwargs)
        self.url = 'https://imglulz.com/'
        self.reset_pagination = False

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.findAll("article", {"class": "post"})[0]
        i = main_content.findAll("img")[1]
        url = i.attrs.get('src')
        t = main_content.find('time')
        img_id = main_content.attrs.get('id').strip('post-')
        timestamp = time.mktime(
            time.strptime(t.attrs.get('datetime'), '%Y-%m-%dT%H:%M:%S+00:00')) - 3600 * UTC_HOUR_DIFF * 2
        images.append({
            "id": img_id,
            "title": i.attrs.get('alt'),
            "url": url,
            "page_url": page_url,
            "created_at": None

        })
        if timestamp < BEGIN_CRAWL_SINCE:
            self.reset_pagination = True
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
                response = requests.get("https://imglulz.com/page/{}".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("article", {"class": "post"})
            for li in list_items:
                link = li.find("a").attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
                    yield link
            status_code = response.status_code
            if self.reset_pagination:
                page = 1
            page += 1

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "created_at": d.get('created_at')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                for g in self.get_galleries():
                    data = self.get_feed(g)
                    pre_processed_data = self._pre_process_data(data)
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                    # if oldest_timestamp < BEGIN_CRAWL_SINCE:
                    #     break
                time.sleep(180)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
