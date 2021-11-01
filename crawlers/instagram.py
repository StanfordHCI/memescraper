import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE

PAGE_SIZE = 256


def graphql(cursor, user_id, headers, page_size=PAGE_SIZE):
    url = 'https://www.instagram.com/graphql/query/?query_hash=42323d64886122307be10013ad2dcc44&variables={"id":"' \
          + user_id + '","first":"' + str(page_size) + '","after":"' + cursor + '"}'
    response = requests.get(url, headers=headers)
    return response


class InstagramCrawler(BaseCrawler):

    def __init__(self, handles, *args, **kwargs):
        super(InstagramCrawler, self).__init__(source='instagram', *args, **kwargs)
        self.url = 'https://www.instagram.com/{}/'
        self.handles = handles
        self.timeout = 16

    def get_feed(self, handle, max_page=1):
        profile = {"handle": handle, "id": None, "edges": []}
        response = requests.get('https://www.instagram.com/{}/'.format(handle))
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            if soup.body is None:
                return profile
            shared_data = json.loads(soup.body.script.get_text().strip(u'window._sharedData =').strip(';'))
            csrf_token = shared_data.get('config', {}).get('csrf_token')
            user = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']
            profile['id'] = user['id']
            profile['media_count'] = user['edge_owner_to_timeline_media']['count']
            profile['followers'] = user['edge_followed_by'].get('count')
            remaining = profile['media_count'] / PAGE_SIZE
            has_next_page = user['edge_owner_to_timeline_media']['page_info']['has_next_page']
            end_cursor = user['edge_owner_to_timeline_media']['page_info']['end_cursor']
            profile['edges'] = user['edge_owner_to_timeline_media']['edges']
            current_page = 1
            if max_page == 1:
                return profile
            while has_next_page and current_page <= max_page:
                current_page += 1
                print("Fetching cursor {}".format(end_cursor))
                print("{} pages remaining for {}".format(remaining, handle))
                graph_response = graphql(end_cursor, profile['id'],
                                         headers={"Cookie": 'csrf_token={}; {}'.format(csrf_token,
                                                                                       'expires=Wed, 29-May-2019 18:37:11 GMT; Max-Age=31449600; Path=/; Secure')})
                if graph_response.status_code == 200:
                    print('-' * 64)
                    g = json.loads(graph_response.content)
                    has_next_page = g['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
                    end_cursor = g['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
                    for e in g['data']['user']['edge_owner_to_timeline_media']['edges']:
                        profile['edges'].append(e)
                    remaining -= 1
                else:
                    time.sleep(32)
                    print("Cursor closed")
                time.sleep(1)

        return profile

    def _pre_process_data(self, handle, data):
        results = []
        for e in data.get('edges', []):
            caption = ''
            try:
                caption = e['node'].get('edge_media_to_caption', {}).get("edges", [{}])[0].get("node", {}).get(
                    "text")
            except:
                pass
            if e['node']['taken_at_timestamp'] >= BEGIN_CRAWL_SINCE:
                results.append(
                    {
                        "id": e['node']['id'],
                        "upvote_count": e['node'].get("edge_liked_by"),
                        "image_url": e['node']['display_url'],
                        "file_name": 'data/instagram/{}/{}.jpg'.format(handle, e['node']['id']),
                        "source": self.source,
                        "created_at": e['node']['taken_at_timestamp'],
                        "child_source": handle,
                        "shortcode": e['node']['shortcode'],
                        "is_video": e['node']['is_video'],
                        "caption": caption,
                        "comment_count": e['node'].get("edge_media_to_comment", {}).get("count")
                    }
                )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                for handle in self.handles:
                    data = self.get_feed(handle)
                    if data is None or not len(data.get("edges", [])):
                        continue
                    try:
                        if data.get('followers') is not None:
                            self.mongo_database.update_source_followers(handle, data.get('followers'))
                    except:
                        self._log_console("Failed to update instagram followers")
                    pre_processed_data = self._pre_process_data(handle, data)
                    self.process_data(pre_processed_data)
                    time.sleep(8)
                    self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
                time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
