# https://hugelol.com/cached/load/fresh.php
# https://hugelol.com/fresh
# curl 'https://hugelol.com/cached/load/fresh.php'  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' --data 'after=579602&target=undefined&q=undefined'
import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE

PAGE_SIZE = 256


class HiddenLolCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):
        super(HiddenLolCrawler, self).__init__(source='hidden_lol', *args, **kwargs)
        self.url = 'https://hiddenlol.com/fresh'
        self.timeout = 16

    def get_feed(self, max_page=10):
        images = []
        response = requests.get(self.url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            first_post = soup.findAll("div", {"class": 'post-container'})[0]
            first_img = first_post.find('img')
            first_id = first_post.attrs.get('data-id')
            has_next_page = True
            images.append({
                "id": first_id,
                "url": first_img.attrs.get('src'),
                "title": first_img.attrs.get('alt'),
                "time": time.mktime(
                    time.strptime(first_post.find('abbr').attrs['title'], '%Y-%m-%dT%H:%M:%S-04:00')) - 10800
            })
            while has_next_page:
                response = requests.post("https://hiddenlol.com/cached/load/fresh.php",
                                         headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                                         data='after={}&target=undefined&q=undefined'.format(first_id))
                if response.status_code == 200:
                    response_data = json.loads(json.loads(response.content))
                    if not len(response_data):
                        has_next_page = False
                    last_post = response_data[len(response_data) - 1]
                    if int(last_post.get('time', 0)) < BEGIN_CRAWL_SINCE:
                        has_next_page = False
                    first_id = last_post['id']
                    for i in response_data:
                        images.append(i)
                else:
                    has_next_page = False
                time.sleep(1)

        return images

    def _pre_process_data(self, data):
        results = []
        for e in data:
            if e['time'] >= BEGIN_CRAWL_SINCE and e.get('repost_of', '0') == '0':
                results.append(
                    {
                        "id": e['id'],
                        "upvote_count": int(e.get('like_amount', 0)) if e.get('like_amount') != '1000' else 0,
                        "image_url": e['url'],
                        "file_name": 'data/{}/{}.jpg'.format(self.source, e['id']),
                        "source": self.source,
                        "created_at": int(e.get('time')),
                        "comment_count": int(e.get('comment_amount', 0)),
                        "title": e.get("title")
                    }
                )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                data = self.get_feed()
                pre_processed_data = self._pre_process_data(data)
                self.process_data(pre_processed_data)
                time.sleep(30)
                self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
