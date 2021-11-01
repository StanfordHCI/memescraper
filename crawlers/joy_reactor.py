import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class JoyReactorCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(JoyReactorCrawler, self).__init__(source='joy_reactor', *args, **kwargs)
        self.url = 'http://joyreactor.com'

    def get_feed(self, page=0, next_path=None):
        images = []
        page_url = '{}/tag/memes/new'.format(self.url)
        if page > 0:
            page_url = '{}{}'.format(self.url, next_path)
        response = requests.get(page_url, headers={'Cookie': 'sfw=1;'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            nav_link = soup.find("a", {"class": "next"})
            if nav_link is not None:
                next_path = nav_link.attrs.get('href')
            posts = soup.findAll("div", {"class": "postContainer"})
            for a in posts:
                try:
                    i = a.find('div', {'class': 'image'}).find('img')
                    t = a.find('span', {'class': 'date'}).find('span')
                    images.append({
                        "id": i.attrs.get('src').split('/')[-1].split('.')[0],
                        "title": i.attrs.get('alt'),
                        "url": i.attrs.get('src'),
                        "created_at": int(t.attrs.get('data-time')) if t.attrs.get('data-time') is not None else None
                    })
                except Exception as e:
                    print(e)

        return images, next_path

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
        next_page = 0
        next_path = None
        while self.running:
            try:
                data, next_path = self.get_feed(next_page, next_path)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(8)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    next_path = None
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
