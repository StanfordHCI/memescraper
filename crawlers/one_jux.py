import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class OneJuxCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(OneJuxCrawler, self).__init__(source='one_jux', *args, **kwargs)
        self.url = 'https://en.1jux.net/tag/meme/1'

    def get_feed(self, page=1, last_post=None):
        images = []
        page_url = self.url
        if page > 1:
            data = {
                "post_level": None,
                "post_id": last_post,
                "task": "tag",
                "tdata[tag]": "meme",
                "tdata[level]": 1,
                "tdata[start]": None
            }
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            response = requests.post("https://en.1jux.net/ajax/tag", data=data, headers=headers)
        else:

            response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.findAll('li', {"class": "post-item"})
            for p in posts:
                try:
                    a = p.find("a", {"class": "post-image"})
                    i = a.find("img")
                    t = p.find("span", {"class": "time"})
                    if 'njf_s.jpg' in i.attrs.get('src'):
                        continue
                    images.append({
                        "id": p.attrs.get("id").strip("post-"),
                        "title": i.attrs.get('alt'),
                        "url": "https://en.1jux.net{}".format(i.attrs.get('src')),
                        "created_at": time.mktime(
                            time.strptime(t.attrs.get("title"), '%Y-%m-%d %H:%M:%S')) - 3600 * (
                                              UTC_HOUR_DIFF + 1)
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
        last_post = None
        while self.running:
            try:
                next_page += 1
                data = self.get_feed(next_page, last_post)
                if len(data):
                    last_post = data[-1]['id']
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    last_post = None
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
