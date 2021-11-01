import json
import time

import requests

from crawlers.generic import BaseCrawler


from settings import NINE_GAG_FREQ


class NineGagCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):
        super(NineGagCrawler, self).__init__(source='nine_gag', *args, **kwargs)
        self.url = 'https://9gag.com/v1/group-posts/group/default/type/'

    def get_feed(self, after='', feed='fresh'):
        response = requests.get(self.url + feed + after)
        if response.status_code == 200:
            return json.loads(response.content)
        return {}

    @staticmethod
    def get_oldest_comment(post_id, order='ts', count=25):
        response = requests.get('https://comment-cdn.9gag.com/v1/cacheable/comment-list.json?'
                                'url=http://9gag.com/gag/{}&count={}&level=2&order={}'
                                '&appId=a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b'.format(post_id, count, order))
        if response.status_code == 200:
            return json.loads(response.content)
        return {}

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'], "upvote_count": d.get('upVoteCount'),
                    "comment_count": d.get('commentsCount'),
                    "image_url": d['images']["image460"]["url"],
                    "file_name": 'data/nine_gag/{}.jpg'.format(d['id']),
                    "nsfw": True if d['nsfw'] else False,
                    "images": d['images'],
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                data = self.get_feed().get('data').get('posts', [])
                pre_processed_data = self._pre_process_data(data)
                self.process_data(pre_processed_data)
                time.sleep(NINE_GAG_FREQ)
                self._log_console("Iteration ended ...")
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
