import time
import uuid

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class FunnyPhotoCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(FunnyPhotoCrawler, self).__init__(source='funny_photo', *args, **kwargs)
        self.url = 'https://funnyfoto.org/funny-pictures/memes/'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.findAll("div", {"class": "td-post-content"})[0]
        imgs = main_content.findAll("img")
        for i in imgs:
            url = i.attrs.get('src')
            img_id = url.split('.')[-1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": page_url
            })
        has_next = False
        try:
            nav_links = main_content.find({"div": {"class": "td-smart-list-pagination"}})
            for l in nav_links.findAll('a'):
                if l.attrs.get('rel')[0] == 'next':
                    has_next = True
        except:
            pass
        return images, has_next

    def get_feed(self, page_url):
        images = []
        status_code = 200
        page = 1
        has_next = True
        while status_code not in [301, 404] and has_next:
            if page == 1:
                response = requests.get(page_url)
            else:
                response = requests.get(page_url + "{}/".format(page), allow_redirects=False)
            status_code = response.status_code
            if response.status_code == 200:
                new_imgs, has_next = self._parse_html(response.content, page_url)
                images = images + new_imgs
            page += 1
        return images

    def get_galleries(self):
        status_code = 200
        galleries = []
        page = 1
        while status_code != 404:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("https://funnyfoto.org/funny-pictures/memes/page/{}".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("div", {"class": "td_module_wrap"})
            for li in list_items:
                link = li.find("a").attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
                    yield link
            status_code = response.status_code
            # page += 1

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
                for g in self.get_galleries():
                    data = self.get_feed(g)
                    pre_processed_data = self._pre_process_data(data)
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        break
                time.sleep(360)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
