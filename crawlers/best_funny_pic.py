import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class BestFunnyPicCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(BestFunnyPicCrawler, self).__init__(source='best_funny_pic', *args, **kwargs)
        self.url = 'https://www.bestfunnypic.com'

    def get_feed(self, data=None, headers=None):
        images = []
        csrf_data = None
        page_url = self.url
        if data is not None:
            response = requests.post('{}/api/more'.format(self.url), data=data, headers=headers)
        else:
            response = requests.get(page_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            if data is not None:
                csrf_data = {
                    "csrf_name": response.headers.get('name'),
                    "csrf_value": response.headers.get('value'),
                    "type": data.get('type'),
                    "url": data.get('url'),
                    "category": data.get('category'),
                    "page": int(data.get('page'))
                }
            else:
                nav_links = soup.find("form", {'id': 'loadMoreForm'})
                if nav_links is not None:
                    csrf_data = {
                        "csrf_name": nav_links.find('input', {"name": "csrf_name"}).attrs.get('value'),
                        "csrf_value": nav_links.find('input', {"name": "csrf_value"}).attrs.get('value'),
                        "type": nav_links.find('input', {"name": "type"}).attrs.get('value'),
                        "url": nav_links.find('input', {"name": "url"}).attrs.get('value'),
                        "category": nav_links.find('input', {"name": "category"}).attrs.get('value'),
                        "page": nav_links.find('input', {"name": "page"}).attrs.get('value')
                    }
            posts = soup.findAll("div", {"class": "grid-item"})
            for a in posts:
                try:
                    i = a.find('img')
                    if i is not None:
                        images.append({
                            "id": i.attrs.get('src').split('/')[-1].split('.')[0],
                            "title": i.attrs.get('alt'),
                            "url": i.attrs.get('src'),
                        })
                except Exception as e:
                    print(e)

        return images, csrf_data, response.headers

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
        csrf_data = None
        headers = None
        while self.running:
            try:
                if csrf_data is not None and csrf_data.get('page') is not None:
                    csrf_data['page'] = int(csrf_data['page']) + 1
                data, csrf_data, response_headers = self.get_feed(csrf_data, headers)
                if 'Set-Cookie' in response_headers:
                    headers = {
                        'Cookie': response_headers.get('Set-Cookie', '').strip('path=/').strip(),
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0',
                        'Referer': 'https://www.bestfunnypic.com/',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if oldest_timestamp < BEGIN_CRAWL_SINCE or csrf_data is None or not inserted:
                    csrf_data = None
                    if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
                        time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
