import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class JustViralCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(JustViralCrawler, self).__init__(source='just_viral', *args, **kwargs)
        self.url = 'https://www.justviral.net/funny/funny-memes/'

    def get_feed(self, g):
        images = []
        response = requests.get(g.get("url"), headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('img')
            pagination = soup.find('div', {"class": "single-split-page"})
            for i in posts:
                try:
                    is_post_img = False
                    img_id = None
                    url = i.attrs.get('src')
                    for c in i.attrs.get("class", []):
                        if c.startswith("wp-image-"):
                            is_post_img = True
                            img_id = c.strip('wp-image-')
                    if not is_post_img:
                        continue
                    images.append({
                        "id": img_id,
                        "title": i.attrs.get('alt'),
                        "url": url
                    })
                except Exception as e:
                    print(e)
            if pagination is not None:
                next_link = None
                for a in pagination.findAll("a"):
                    if a.attrs.get("href") > g.get("url"):
                        next_link = a.attrs.get("href")
                        break
                if next_link is not None:
                    images = images + self.get_feed({"url": next_link})

        return images

    def get_galleries(self):
        response = requests.get(self.url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        list_items = soup.findAll("div", {"class": "post"})
        for li in list_items:
            yield {
                "id": li.attrs.get("id").strip("post-"),
                "url": li.find("figure").find("a").attrs.get("href")
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

                time.sleep(120)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
