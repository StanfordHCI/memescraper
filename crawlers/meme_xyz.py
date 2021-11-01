import json
import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE


class MemeXYZCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(MemeXYZCrawler, self).__init__(source='meme_xyz', *args, **kwargs)
        self.url = 'https://meme.xyz/fresh'

    def _parse_html(self, html_content):
        images = []
        soup = BeautifulSoup(html_content, 'html.parser')
        imgs_html = soup.findAll("img", {"class": "badge-item-img"})
        for i in imgs_html:
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            url_parts = i.attrs.get('src').split('/')
            img_id = url_parts[len(url_parts) - 1].split('-')[1]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url
            })
        return images

    def get_feed(self, page=0):
        images = []
        if page == 0:
            page = ''
            response = requests.get(self.url.format(page))
            if response.status_code == 200:
                images = self._parse_html(response.content)
        else:
            page_url = "https://meme.xyz/json.php?section=vote&page={}&json=1".format(page)
            response = requests.get(page_url)
            if response.status_code == 200:
                json_content = json.loads(response.content)
                image_ids = json_content.get("ids", [])
                for img_id in image_ids:
                    i_response = requests.get("https://meme.xyz/meme/{}/".format(img_id))
                    if i_response.status_code == 200:
                        for i in self._parse_html(i_response.content):
                            images.append(i)
        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/meme_xyz/{}.jpg'.format(d['id']),
                    "source": self.source
                }
            )
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        next_page = 0
        while self.running:
            try:
                data = self.get_feed(next_page)
                next_page += 1
                pre_processed_data = self._pre_process_data(data)
                self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if next_page >= MAX_PAGE:
                    next_page = 0
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
