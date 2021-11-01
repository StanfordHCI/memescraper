import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class QuoraTreasuryCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(QuoraTreasuryCrawler, self).__init__(source='quora_treasury', *args, **kwargs)
        self.url = 'http://www.quoratreasury.com/p/more-memes_50.html'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.findAll("div", {"class": "post-body"})[0]
        imgs = main_content.findAll("img")
        for i in imgs:
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            img_id = i.attrs.get("src").split('/')[6]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "post_id": page_url
            })
        return images

    def get_feed(self, page_url):
        images = []
        response = requests.get(page_url)
        if response.status_code == 200:
            images = self._parse_html(response.content, page_url)

        return images

    def get_pages(self):
        galleries = []
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        post = soup.find("div", {"class": "post"})
        list_items = post.findAll("a")
        for li in list_items:
            link = li.attrs.get("href")
            if link not in galleries and link is not None:
                galleries.append(link)
        return galleries

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                galleries = self.get_pages()
                for g in galleries:
                    data = self.get_feed(g)
                    pre_processed_data = self._pre_process_data(data)
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                    time.sleep(4)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        break
                time.sleep(180)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
