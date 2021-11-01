import time
import facebook
from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF, FACEBOOK_ACCESS_TOKEN, FACEBOOK_TIMEOUT


class FacebookCrawler(BaseCrawler):

    def __init__(self, pages, *args, **kwargs):
        super(FacebookCrawler, self).__init__(source='facebook', *args, **kwargs)
        self.url = 'https://www.facebook.com/{}/'
        self.pages = pages
        self.timeout = FACEBOOK_TIMEOUT
        self.graph = facebook.GraphAPI(
            access_token=FACEBOOK_ACCESS_TOKEN,
            version="3.1")

    def get_feed(self, page_id):
        meme_posts = self.graph.request('/{}/posts/'.format(page_id),
                                        {'limit': 100,
                                         'fields': "id,message,created_time,updated_time,full_picture,caption,permalink_url,type,object_id,shares"})
        post_data = meme_posts.get("data", [])
        return post_data

    def _pre_process_data(self, page_id, data):
        results = []
        for e in data:
            try:
                create_at_t = time.mktime(
                    time.strptime(e['created_time'], '%Y-%m-%dT%H:%M:%S+0000'))  # - UTC_HOUR_DIFF * 3600
                if create_at_t >= BEGIN_CRAWL_SINCE and e.get('type', 'photo') == 'photo':
                    results.append(
                        {
                            "id": e.get('id'),
                            "object_id": e.get('object_id'),
                            "image_url": e.get("full_picture"),
                            "post_url": e.get("permalink_url"),
                            "file_name": 'data/{}/{}/{}.jpg'.format(self.source, page_id, e['id']),
                            "source": self.source,
                            "created_at": create_at_t,
                            "child_source": page_id,
                            "caption": e.get('message'),
                            "shares_count": e.get("shares", {}).get("count")
                        }
                    )
            except:
                print("facebook {} failed to preprocess data".format(page_id))
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                for page in self.pages:
                    try:
                        data = self.get_feed(page['id'])
                        try:
                            self.mongo_database.update_facebook_page_activity(page['id'], time.time())
                        except Exception as e:
                            pass
                        pre_processed_data = self._pre_process_data(page['id'], data)
                        self.process_data(pre_processed_data)
                        self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
                    except Exception as e:
                        pass
                    time.sleep(self.timeout)
                time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
