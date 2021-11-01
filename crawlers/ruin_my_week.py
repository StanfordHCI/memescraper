import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler


class RuinMyWeekCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(RuinMyWeekCrawler, self).__init__(source='ruin_my_week', *args, **kwargs)
        self.url = 'https://ruinmyweek.com/category/memes/'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.find("div", {"class": "thecontent"})
        imgs = main_content.findAll("img")
        for i in imgs:
            url = i.attrs.get('src')
            img_class = i.attrs.get("class")
            if not len(img_class):
                continue
            is_wp_image = False
            img_id = None
            for c in img_class:
                if "wp-image" in c:
                    is_wp_image = True
                    img_id = c.strip('wp-image-')
            if not is_wp_image:
                continue
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": page_url
            })
        return images

    def get_feed(self, page_url):
        images = []
        response = requests.get(page_url)
        if response.status_code == 200:
            images = self._parse_html(response.content, page_url)
        return images

    def get_galleries(self):
        status_code = 200
        galleries = []
        page = 1
        while status_code != 404:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("https://ruinmyweek.com/category/memes/page/{}/".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("article", {"class": "latestPost"})
            for li in list_items:
                link = li.find("a").attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
            status_code = response.status_code
            page += 1
        return galleries

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
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                galleries = self.get_galleries()
                for g in galleries:
                    data = self.get_feed(g)
                    pre_processed_data = self._pre_process_data(data)
                    self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(360)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
