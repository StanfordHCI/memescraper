import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class SlowRobotCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(SlowRobotCrawler, self).__init__(source='slow_robot', *args, **kwargs)
        self.url = 'https://slowrobot.com'

    def get_feed(self, page=1):
        images = []
        page_url = self.url
        if page > 1:
            page_url = '{}/p/{}/'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll("div", {"class": "sub_container"})
            for a in posts:
                link = a.find('a')
                try:
                    i = a.find('img')
                    images.append({
                        "id": link.attrs.get('href').split('/')[-1],
                        "title": i.attrs.get('alt'),
                        "url": i.attrs.get('src')
                    })
                except Exception as e:
                    print(e)

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
                    "source": self.source,
                    "created_at": d.get('created_at')
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
                time.sleep(4)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    time.sleep(8)
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
