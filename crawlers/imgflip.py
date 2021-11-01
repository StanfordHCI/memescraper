import time

import requests
from bs4 import BeautifulSoup

from crawlers.generic import BaseCrawler
from settings import MAX_PAGE, BEGIN_CRAWL_SINCE


def get_latest_imgflip(page=0):
    images = []
    if page > 0:
        page = '&page={}'.format(page)
    else:
        page = ''
    response = requests.get('https://imgflip.com/?sort=latest{}'.format(page))
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        imgs_html = soup.findAll("img", {"class": "base-img"})
        for i in imgs_html:
            if i.attrs.get('src')[:2] == '//':
                url = 'https:' + i.attrs.get('src')
            else:
                url = i.attrs.get('src')
            url_parts = i.attrs.get('src').split('/')
            img_id = url_parts[len(url_parts) - 1].split('.')[0]
            images.append({
                "id": img_id,
                "title": i.attrs.get('alt'),
                "url": url
            })

    return images


class ImgFlipCrawler(BaseCrawler):
    def __init__(self, *args, **kwargs):
        super(ImgFlipCrawler, self).__init__(source='imgflip', *args, **kwargs)
        self.url = 'https://imgflip.com/?sort=latest{}'

    def get_feed(self, page=0):
        images = []
        if page > 0:
            page = '&page={}'.format(page)
        else:
            page = ''
        response = requests.get(self.url.format(page))
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            imgs_html = soup.findAll("img", {"class": "base-img"})
            for i in imgs_html:
                if i.attrs.get('src')[:2] == '//':
                    url = 'https:' + i.attrs.get('src')
                else:
                    url = i.attrs.get('src')
                url_parts = i.attrs.get('src').split('/')
                img_id = url_parts[len(url_parts) - 1].split('.')[0]
                images.append({
                    "id": img_id,
                    "title": i.attrs.get('alt'),
                    "url": url
                })

        return images

    def _pre_process_data(self, data):
        results = []
        for d in data:
            results.append(
                {
                    "id": d['id'],
                    "title": d.get('title'),
                    "image_url": d.get('url'),
                    "file_name": 'data/imgflip/{}.jpg'.format(d['id']),
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
                inserted, oldest_timestamp = self.process_data(pre_processed_data)
                self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
                time.sleep(4)
                if next_page >= MAX_PAGE or oldest_timestamp < BEGIN_CRAWL_SINCE:
                    next_page = 0
                    time.sleep(30)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
