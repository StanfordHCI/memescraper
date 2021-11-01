import json
import time

import requests

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


class CheezBurgerCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(CheezBurgerCrawler, self).__init__(source='cheez_burger', *args, **kwargs)
        self.url = 'https://memebase.cheezburger.com/api/search?q=memes&page={}&pageSize=64&assetTypeId=0'

    def get_feed(self, page_nr):
        images = []
        response = requests.get(self.url.format(page_nr))
        if response.status_code == 200:
            response_json = json.loads(response.content).get("models")
            for m in response_json:
                images.append({
                    "id": m.get("asset_id"),
                    "post_url": m.get("post_url"),
                    "source_domain": m.get("source_name"),
                    "title": m.get("title"),
                    "url": m.get("url").replace("thumb400", "full")
                })

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
                    "source_domain": d.get("source_domain")
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
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
