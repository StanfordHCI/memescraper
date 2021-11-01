# import time
#
# import requests
# from bs4 import BeautifulSoup
#
# from crawlers.generic import BaseCrawler
# from settings import BEGIN_CRAWL_SINCE
#
#
# class EvilMilkCrawler(BaseCrawler):
#     def __init__(self, *args, **kwargs):
#         super(EvilMilkCrawler, self).__init__(source='evil_milk', *args, **kwargs)
#         self.url = 'https://www.evilmilk.com/'
#
#     def get_feed(self, page=1):
#         images = []
#         page_url = 'https://www.evilmilk.com/archive/page{}.htm'.format(page)
#         response = requests.get(page_url)
#         if response.status_code == 200:
#             soup = BeautifulSoup(response.content, 'html.parser')
#             posts = soup.findAll('img', {"class": "size-full"})
#             for i in posts:
#                 try:
#                     img_id = [c for c in i.attrs.get('class', []) if c.startswith('wp-image-')][0].strip('wp-image-')
#                     images.append({
#                         "id": img_id,
#                         "title": i.attrs.get('alt'),
#                         "url": i.attrs.get('src')
#                     })
#                 except Exception as e:
#                     print(e)
#
#         return images
#
#     def _pre_process_data(self, data):
#         results = []
#         for d in data:
#             results.append(
#                 {
#                     "id": d['id'],
#                     "title": d.get('title'),
#                     "image_url": d.get('url'),
#                     "file_name": 'data/{}/{}.jpg'.format(self.source, d['id']),
#                     "source": self.source,
#                     "created_at": d.get('created_at')
#                 }
#             )
#         return results
#
#     def run(self):
#         self._log_console("Starting up {} crawler ...".format(self.source))
#         self._create_mongo_db_connection()
#         next_page = 0
#         while self.running:
#             try:
#                 next_page += 1
#                 data = self.get_feed(next_page)
#
#                 pre_processed_data = self._pre_process_data(data)
#                 inserted, oldest_timestamp = self.process_data(pre_processed_data)
#                 self._log_console("Iteration ended with {} results".format(len(pre_processed_data)))
#                 time.sleep(4)
#                 if oldest_timestamp < BEGIN_CRAWL_SINCE or not inserted:
#                     next_page = 0
#                     if (oldest_timestamp - BEGIN_CRAWL_SINCE) > 300:
#                         time.sleep(60)
#             except Exception as e:
#                 print(e)
#                 self._log_console("Exception on main thread run()")
