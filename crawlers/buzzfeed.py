import json
import time

import requests

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class BuzzFeedCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(BuzzFeedCrawler, self).__init__(source='buzzfeed', *args, **kwargs)
        self.url = 'https://www.buzzfeed.com/site-component/v1/en-us/morebuzz?page={}&page_size=64&image_crop=wide'

    def get_feed(self, page_nr):
        images = []
        response = requests.get(self.url.format(page_nr), headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            images = json.loads(response.content).get("results", [])
        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('name'),
                    "image_url": d.get('image'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "page_url": "https://buzzfeed.com{}".format(d.get("canonical_path")),
                    "created_at": time.mktime(
                        time.strptime(d.get("created_at"), '%Y-%m-%dT%H:%M:%SZ')) - UTC_HOUR_DIFF * 3600
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        page = 1
        while self.running:
            try:
                data = self.get_feed(page_nr=page)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                page += 1
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    page = 1
                    time.sleep(60)
                time.sleep(180)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
