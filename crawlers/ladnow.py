import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class LadnowCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(LadnowCrawler, self).__init__(source='ladnow', *args, **kwargs)
        self.url = 'http://ladnow.com/category/funny/'

    def _parse_html(self, html_content, page_url):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        figures = soup.findAll("figure", {"class": "wp-caption"})
        # figures = main_content.findAll("img")
        for f in figures:
            i = f.find("img")
            cap = f.find("figcaption")
            source_domain = None
            if cap is not None:
                source_domain = cap.find("a").attrs.get("href")
            url = i.attrs.get('src')
            img_class = i.attrs.get("class", [])
            if len(img_class) < 2:
                continue
            if "wp-image" not in img_class[1]:
                continue
            class_parts = img_class[1].split("-")
            img_id = class_parts[len(class_parts) - 1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "page_url": page_url,
                "source_domain": source_domain
            })
        nav_links = soup.find("div", {"class": "theiaPostSlider_nav"})
        has_next = True
        if nav_links is not None:
            a = nav_links.find("a", {"rel": "next"})
            if a is not None:
                has_next = '_another_post' not in a.attrs.get("class", [])
        return images, has_next

    def get_feed(self, page_url):
        images = []
        status_code = 200
        page = 1
        has_next = True
        while status_code not in [301, 404] and has_next:
            if page == 1:
                response = requests.get(page_url)
            else:
                response = requests.get(page_url + "{}/".format(page), allow_redirects=False)
            status_code = response.status_code
            if response.status_code == 200:
                new_imgs, has_next = self._parse_html(response.content, page_url)
                images = images + new_imgs
            page += 1

        return images

    def get_galleries(self):
        status_code = 200
        galleries = []
        page = 1
        while status_code != 404:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("http://ladnow.com/category/funny/page/{}/".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("li", {"class": "post-item"})
            for li in list_items:
                link = li.find("a").attrs.get("href")
                if link not in galleries:
                    galleries.append(link)
                    yield link
            status_code = response.status_code
            page += 1

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
                    "source_domain": d.get("source_domain"),
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
                    inserted, oldest_timestamp = self.process_data(pre_processed_data)
                    self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                    time.sleep(8)
                    if oldest_timestamp < BEGIN_CRAWL_SINCE:
                        break
                time.sleep(180)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
