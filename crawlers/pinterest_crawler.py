import time

from pinterest import Pinterest

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, PINTEREST_EMAIL, PINTEREST_PWD


class PinterestCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(PinterestCrawler, self).__init__(source='pinterest', *args, **kwargs)
        self.url = 'https://www.pinterest.com/search/pins/?q=memes'
        self.pinterest_provider = Pinterest(username_or_email=PINTEREST_EMAIL, password=PINTEREST_PWD)
        self.pinterest_provider.login()

    def get_feed(self, page=0):
        next_page = page > 0
        pins = self.pinterest_provider.search("pins", "memes", next_page=next_page)
        return pins

    def _pre_process_data(self, data):
        results = []
        for result in data:
            if result['type'] == 'pin':
                results.append({
                    "file_name": 'data/pinterest/{}.jpg'.format(result['id']),
                    'id': result['id'],
                    'title': result['description'],
                    'image_url': result['images']['orig']['url'],
                    'source_link': result['link'],
                    'source_domain': result.get("domain"),
                    'source': self.source,
                    'created_at': time.mktime(time.strptime(result.get("created_at"), '%a, %d %b %Y %H:%M:%S +0000'))
                })
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        while self.running:
            try:
                data = self.get_feed(next_page)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(5)
                if next_page >= MAX_PAGE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
