import json
import time

import requests

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE

IMGUR_BASE_URL = 'https://api.imgur.com/3/gallery/t/funny/time/week/{}?IMGURPLATFORM=web&client_id=8b28f8156bc9ab0'


# def get_imgur_feed(page=0):
#     response = requests.get(IMGUR_BASE_URL.format(page))
#     if response.status_code == 200:
#         return json.loads(response.content)
#     return {}


class ImgurCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):
        super(ImgurCrawler, self).__init__(source='imgur', *args, **kwargs)
        self.url = IMGUR_BASE_URL

    def get_feed(self, page=0):
        response = requests.get(self.url.format(page))
        if response.status_code == 200:
            return json.loads(response.content)
        return {}

    def _pre_process_data(self, data):
        results = []
        for d in data:
            if d.get('animated', False):
                continue
            images = []
            if 'images' not in d:
                link = d.get('link')
            else:
                link = d['images'][0]['link']
                images = d['images']
            results.append(
                {
                    "id": d['id'],
                    "upvote_count": d.get('ups'),
                    "downvote_count": d.get('downs'),
                    "comment_count": d.get('comment_count'),
                    "points": d.get('points'),
                    "score": d.get('score'),
                    "image_url": link,
                    "file_name": 'data/imgur/{}.jpg'.format(d['id']),
                    "nsfw": d.get('nsfw'),
                    "images": images,
                    "source": self.source,
                    "url": d['link'],
                    "created_at": d.get('datetime')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        while self.running:
            try:
                data = self.get_feed(next_page).get('data').get('items', [])
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                time.sleep(8)
                self._log_console("Iteration ended ...")
                next_page += 1
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    time.sleep(16)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
