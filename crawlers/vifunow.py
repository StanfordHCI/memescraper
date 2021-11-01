import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler


class VifunowCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(VifunowCrawler, self).__init__(source='vifunow', *args, **kwargs)
        self.url = 'https://vifunow.com/?s=memes'

    def _parse_html(self, html_content):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = soup.findAll("div", {"class": "theiaPostSlider_slides"})[0]
        imgs = main_content.findAll("img")
        post_id = None
        for i in imgs:
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            img_class = i.attrs.get("class")
            if not len(img_class):
                continue
            if "wp-image" not in img_class[0]:
                continue
            class_parts = img_class[0].split("-")
            img_id = class_parts[len(class_parts) - 1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url,
                "post_id": i.attrs.get("data-frizzly-image-post-id")
            })
            post_id = i.attrs.get("data-frizzly-image-post-id")
        next_url = None
        if post_id is not None:
            nav = soup.find("div", {"id": "tps_nav_lower_{}".format(post_id)}).find("a", {"class": "_next"})
            if nav is None or "_disabled" in nav.attrs.get("class", []):
                pass
            else:
                next_url = nav.attrs.get("href")
        return images, next_url

    def get_feed(self, page_url):
        images = []
        status_code = 200
        while status_code not in [301, 404] and page_url is not None:
            response = requests.get(page_url)
            status_code = response.status_code
            if response.status_code == 200:
                new_imgs, page_url = self._parse_html(response.content)
                images = images + new_imgs

        return images

    def get_galleries(self):
        status_code = 200
        galleries = []
        page = 1
        while status_code != 404:
            if page == 1:
                response = requests.get(self.url)
            else:
                response = requests.get("https://vifunow.com/page/{}/?s=memes".format(page))
            soup = BeautifulSoup(response.content, 'html.parser')
            list_items = soup.findAll("li", {"class": "mvp-blog-story-wrap"})
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
                    "file_name": 'data/vifunow/{}.jpg'.format(d['id']),
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
