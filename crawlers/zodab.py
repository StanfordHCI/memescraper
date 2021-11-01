import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class ZodabCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(ZodabCrawler, self).__init__(source='zodab', *args, **kwargs)
        self.url = 'https://zodab.com/memes'

    def get_feed(self, page=1):
        images = []
        page_url = 'https://zodab.com/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=9.5'
        data = {
            "action": "td_ajax_loop",
            "loopState[sidebarPosition]": "no_sidebar",
            "loopState[moduleId]": 11,
            "loopState[currentPage]": page,
            "loopState[max_num_pages]": 51,
            "loopState[atts][category_id]": 27,
            "loopState[atts][offset]": 5,
            "loopState[ajax_pagination_infinite_stop]": 0,
            "loopState[server_reply_html_data]": None
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0',
            'Referer': 'https://zodab.com/memes',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        response = requests.post(page_url, headers=headers, data=data)
        if response.status_code == 200:
            soup = BeautifulSoup(
                json.loads(response.content).get('server_reply_html_data').replace('\n', '').replace('\r', ''),
                'html.parser')
            posts = soup.findAll('div', {"class": "td_module_wrap"})
            for p in posts:
                try:
                    i = p.find("img")
                    t = p.find("time", {"class": "entry-date"})
                    img_id = i.attrs.get('src').split('/')[-1].split('.')[0]
                    images.append({
                        "id": img_id,
                        "title": i.attrs.get('alt'),
                        "url": i.attrs.get('src'),
                        "created_at": time.mktime(
                            time.strptime(t.attrs.get("datetime"), '%Y-%m-%dT%H:%M:%S+00:00')) - 3600 * UTC_HOUR_DIFF
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
        while self.running:
            try:
                next_page += 1
                data = self.get_feed(next_page)

                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(30)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
                    next_page = 0
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)

            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
