import json
import os
import signal
import time
from datetime import datetime
from threading import Thread

import redis
import requests
from google.cloud import vision

from crawlers.storage import MongoDatabase
from settings import MONGODB_URL, MONGODB_NAME, WS4REDIS_EXPIRE, DATA_ROOT_PATH, UTC_HOUR_DIFF
from utils import sha256_checksum, annotate_text, annotate_web, RedisPublisher, RedisMessage, detect_safe_search


class BaseCrawler(Thread):
    running = True
    google_client = None

    def __init__(self, *args, **kwargs):
        super(BaseCrawler, self).__init__()
        self.source = kwargs.get('source').lower()
        self.google_queue = kwargs.get('google_queue')
        self.redis_publisher = RedisPublisher(facility='notifications', broadcast=True)

    def download_and_store_file(self, file_name, url, override=False, attempt=1):
        if not os.path.exists('{}/{}'.format(DATA_ROOT_PATH, file_name)) or override:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 404:
                    return None
                else:
                    print("Saving {}".format(file_name))
                    print("-" * 64)
                    with open('{}/{}'.format(DATA_ROOT_PATH, file_name), 'wb') as f:
                        f.write(response.content)
                    return response.headers
            except requests.exceptions.ConnectionError:
                time.sleep(2)
                if attempt < 4:
                    self.download_and_store_file(file_name, url, override, attempt + 1)
            except requests.exceptions.Timeout:
                time.sleep(2)
                if attempt < 4:
                    self.download_and_store_file(file_name, url, override, attempt + 1)
            except Exception as e:

                print(e)
        return None

    def publish_websocket_message(self, message, expire=WS4REDIS_EXPIRE):
        redis_message = RedisMessage(json.dumps(message))
        try:
            self.redis_publisher.publish_message(redis_message, expire)
        except redis.exceptions.ConnectionError as e:
            print(e)

    def _log_console(self, message):
        print('[{}] ({}) '.format(self.source, datetime.now()) + message)
        self.publish_websocket_message({"source": self.source, "message": message, "event": "log_created"})

    def _register_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGABRT, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum in [signal.SIGINT, signal.SIGHUP]:
            self.running = False

    def _create_mongo_db_connection(self):
        self.mongo_database = MongoDatabase(connection_url=MONGODB_URL, db_name=MONGODB_NAME)

    def get_text_regions(self, filename):
        annotations = annotate_text(self.google_client, filename)
        text_regions = []
        for a in annotations:
            t = {'description': a.description, 'locale': a.locale}
            poly = []
            for v in a.bounding_poly.vertices:
                poly.append({"x": v.x, "y": v.y})

            t['bounding_poly'] = poly
            text_regions.append(t)
        return text_regions

    def get_web_detection(self, filename):
        annotations = annotate_web(self.google_client, filename)
        full_matching_images = []
        if annotations.full_matching_images:
            for a in annotations.full_matching_images:
                full_matching_images.append({"url": a.url, "score": a.score})
        return full_matching_images

    def is_safe_content(self, url):
        safe = detect_safe_search(self.google_client, url)
        likelihood_name = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE',
                           'LIKELY', 'VERY_LIKELY')
        result = {
            "adult": likelihood_name[safe.adult],
            "medical": likelihood_name[safe.medical],
            "spoofed": likelihood_name[safe.spoof],
            "violence": likelihood_name[safe.violence],
            "racy": likelihood_name[safe.racy]
        }
        if safe.adult > 2 or safe.racy > 2:
            return False, result

        return True, result

    def process_data(self, data):
        inserted = False
        oldest_timestamp = time.time()
        if self.google_client is None:
            self.google_client = vision.ImageAnnotatorClient()
        for d in data:
            exists = self.mongo_database.find_image_by_src(source=self.source, img_id=d['id'])
            if exists and len(exists):
                exists['last_updated_at'] = time.time()
                exists['upvote_count'] = d.get('upvote_count')
                self.mongo_database.db.images.update_one({"_id": exists['_id']}, {"$set": exists}, upsert=False)
            else:
                is_safe = True
                google_safe_result = {}
                if self.source == 'four_chan':

                    is_safe, google_safe_result = self.is_safe_content(d.get('image_url'))
                    d.update(
                        {
                            "first_seen_at": time.time(),
                            "google_safe_search": google_safe_result,
                            "is_safe": is_safe
                        }
                    )
                    if not is_safe:
                        d.update({"deleted": True})
                        self.mongo_database.create_image(d)
                        continue
                headers = self.download_and_store_file(d.get('file_name'), d.get('image_url'), override=True)
                if headers is None:
                    print("Skipping .. {}".format(d['id']))
                    continue
                if headers.get('last-modified') is not None and d.get('created_at') is None:
                    d['created_at'] = time.mktime(
                        time.strptime(headers.get('last-modified'), '%a, %d %b %Y %H:%M:%S GMT')) - 3600 * UTC_HOUR_DIFF
                if headers.get("age") is not None and d.get("created_at") is None:
                    d['created_at'] = time.time() - int(headers.get("age"))
                sha256 = None
                # text_regions = []
                # full_matching_images = []
                if os.path.exists(d.get('file_name')):
                    sha256 = sha256_checksum(d.get('file_name'))
                    # text_regions = self.get_text_regions(d.get('file_name'))
                    # full_matching_images = self.get_web_detection(d.get('file_name'))
                d.update(
                    {
                        "first_seen_at": time.time(),
                        "sha256": sha256,
                        "google_query_completed": False
                        # "text_regions": text_regions,
                        # "full_matching_images": full_matching_images
                    }
                )
                # if len(text_regions):
                #     d.update({"text": text_regions[0]['description']})
                if d.get('created_at') is None:
                    d['created_at'] = d['first_seen_at']
                    d['exact_time'] = False
                if d['created_at'] < oldest_timestamp:
                    oldest_timestamp = d['created_at']
                img = self.mongo_database.create_image(d)
                self.google_queue.put({"_id": img.inserted_id})
                self._log_console("Fetched {} from {}".format(d['id'], self.source))
                inserted = True
        return inserted, oldest_timestamp
