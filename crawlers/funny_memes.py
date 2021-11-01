import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE, UTC_HOUR_DIFF


class FunnyMemesCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(FunnyMemesCrawler, self).__init__(source='funny_memes', *args, **kwargs)
        self.url = 'https://funnymemes.co/'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = soup.findAll("article")
        for article in articles:
            a = article.find("a")
            i = article.find("img")
            tm = article.find("time")
            if i is None or '.gif' in i.attrs.get('src'):
                continue
            url = i.attrs.get('src')
            img_id = article.attrs.get("id", '').split('-')[1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": a.attrs.get("href"),
                "created_at": tm.attrs.get("datetime")
            })
        return images

    def get_feed(self, page_url):
        images = []
        response = requests.get(page_url)
        if response.status_code == 200:
            images = self._parse_html(response.content, page_url)
        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "page_url": d.get('page_url'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source,
                    "created_at": time.mktime(
                        time.strptime(d.get("created_at"), '%Y-%m-%dT%H:%M:%S+00:00')) - UTC_HOUR_DIFF * 3600
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
                if next_page == 1:
                    url = self.url
                else:
                    url = self.url + 'page/{}'.format(next_page)
                data = self.get_feed(url)
                pre_processed_data = self._pre_process_data(data)
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                # time.sleep(360)
                time.sleep(4)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
