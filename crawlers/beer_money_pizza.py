import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class BeerMoneyPizzaCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(BeerMoneyPizzaCrawler, self).__init__(source='beer_money_pizza', *args, **kwargs)
        self.url = 'https://beermoneypizza.com/category/funny/'

    def get_feed(self, page=0):
        images = []
        page_url = self.url
        if page > 1:
            page_url = '{}page/{}/'.format(self.url, page)
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.findAll("article", {"class": "post"})
            for a in articles:
                try:
                    i = a.find('img')
                    t = a.find('time')
                    article_classes = a.attrs.get('class', [])
                    img_id = None
                    for c in article_classes:
                        if c.startswith('post-'):
                            img_id = c.split('-')[-1]
                    images.append({
                        "id": img_id,
                        "title": i.attrs.get('alt'),
                        "url": i.attrs.get('src'),
                        "created_at": time.mktime(
                            time.strptime(t.attrs.get('datetime'), '%Y-%m-%dT%H:%M:%S')) - 3600 * 3
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
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
