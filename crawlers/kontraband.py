import json
import time

import requests

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class KontrabandCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(KontrabandCrawler, self).__init__(source='kontraband', *args, **kwargs)
        self.url = 'https://api2.kontraband.com/type/0/category/comedy?device=desktop&page={}'

    def get_feed(self, page_nr):
        images = []
        response = requests.get(self.url.format(page_nr))
        if response.status_code == 200:
            response_json = json.loads(response.content)
            for m in response_json:
                if m.get('nsfw', False) or m.get('referenceType') != "Image":
                    continue
                images.append({
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "slug": m.get("slug"),
                    "url": 'https://cdn10.kontraband.com/uploads/images/{}'.format(m.get('teaserImage')),
                    "created_at": time.mktime(
                        time.strptime(m.get("publishDate") or m.get('updatedAt'), '%Y-%m-%dT%H:%M:%S+01:00')) - (
                                              UTC_HOUR_DIFF + 1) * 3600
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
                time.sleep(8)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
