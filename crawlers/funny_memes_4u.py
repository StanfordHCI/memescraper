import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class FunnyMemes4UCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(FunnyMemes4UCrawler, self).__init__(source='funny_memes_4u', *args, **kwargs)
        self.url = 'https://funnymemes4u.com/category/funny-memes/'

    def get_feed(self, g):
        images = []
        response = requests.get(g.get("url"), headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('img')
            pagination = soup.find("div", {"class": "pagination"})

            for i in posts:
                try:
                    url = i.attrs.get('data-layzr')
                    is_post_img = False
                    for c in i.attrs.get("class", []):
                        if c.startswith("wp"):
                            is_post_img = True
                    if not is_post_img:
                        continue
                    images.append({
                        "id": i.attrs.get("data-attachment-id"),
                        "title": i.attrs.get('alt'),
                        "url": url
                    })
                except Exception as e:
                    print(e)
            if pagination is not None:
                if pagination.findAll("a")[-1].attrs.get("href") > g.get("url"):
                    images = images + self.get_feed({"url": pagination.findAll("a")[-1].attrs.get("href")})

        return images

    def get_galleries(self):
        response = requests.get(self.url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        list_items = soup.findAll("article")
        for li in list_items:
            yield {
                "id": '',
                "url": li.find("a").attrs.get("href")
            }

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
                    if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                        time.sleep(180)
                        break
                    time.sleep(10)
                time.sleep(120)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
