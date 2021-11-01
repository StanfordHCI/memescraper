import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class SomeEcardsCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(SomeEcardsCrawler, self).__init__(source='some_ecards', *args, **kwargs)
        self.url = 'https://www.someecards.com/memes-lists-comics/'

    def get_feed(self, g):
        images = []
        page_url = "https://www.someecards.com/memes-lists-comics/memes/{}/".format(g.get("url"))
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('figure', {"class": "image"})
            for p in posts:
                try:
                    i = p.find("img")
                    if i.attrs.get('src')[:2] == '//':
                        url = 'https:' + i.attrs.get('src')
                    else:
                        url = i.attrs.get('src')
                    img_id = i.attrs.get('src').split('/')[-1].split('.')[0]
                    images.append({
                        "id": img_id,
                        "title": i.attrs.get('alt'),
                        "url": url,
                        "created_at": g.get("created_at")
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

    def get_galleries(self):
        response = requests.get(
            "https://napi.someecards.com/apife/getSectionEntities/?slug=memes-lists-comics&limit=48")
        if response.status_code == 200:
            list_items = json.loads(response.content).get('items').get('listItems', [])
            for li in list_items:
                post_date = time.mktime(
                    time.strptime(li.get('postDate').get("date"), '%Y-%m-%d %H:%M:%S.000000')) - 3 * 3600
                if post_date >= BEGIN_CRAWL_SINCE:
                    yield {
                        "id": li.get("id"),
                        "url": li.get("slug"),
                        "created_at": post_date,
                        "headline": li.get("headline"),

                    }

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
                time.sleep(120)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
