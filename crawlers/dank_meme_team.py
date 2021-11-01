import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class DankMemeTeamCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(DankMemeTeamCrawler, self).__init__(source='dank_meme_team', *args, **kwargs)
        self.url = 'http://dankmemeteam.com/'

    def _parse_html(self, html_content, page=0):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        next_query = ''
        containers = soup.findAll("li", {"class": "g1-collection-item"})
        for c in containers:
            item = c.find("article")
            if item is None:
                continue
            i = c.find_all("img")[0]
            t = c.find("time")
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            images.append({
                "id": item.attrs.get('id', '').strip("post-"),
                "title": i.attrs.get('alt'),
                "url": url,
                "time": time.mktime(time.strptime(t.attrs.get("datetime"), '%Y-%m-%dT%H:%M:%S')) - UTC_HOUR_DIFF * 3600
            })
        return images, next_query

    def get_feed(self, page=0, next_query=''):
        images = []
        if page == 0:
            page_url = self.url
        else:
            page_url = "http://dankmemeteam.com{}".format(next_query)

        response = requests.get(page_url)
        if response.status_code == 200:
            images, next_query = self._parse_html(response.content, page=page)

        return images, next_query

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
                    "created_at": d.get('time')
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        next_page_query = ''
        while self.running:
            try:
                data, next_page_query = self.get_feed(next_page, next_page_query)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    next_page_query = ''
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
                time.sleep(16)
