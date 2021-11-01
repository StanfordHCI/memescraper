from pymongo import MongoClient


class MongoDatabase(object):
    client = None
    db = None

    def __init__(self, connection_url, db_name='meme_id'):
        self.client = MongoClient(connection_url)
        self.db = self.client[db_name]

    def find_image_by_src(self, img_id, source):
        return self.db.images.find_one({"id": img_id, "source": source})

    def create_image(self, image):
        return self.db.images.insert_one(image)

    def update_source_followers(self, source_name, followers=None, max_likes=None):
        return self.db.sources.update({"name": source_name}, {"$set": {"followers": followers, "max_likes": max_likes}},
                                      upsert=False)

    def get_upvotes_by_source(self, source, child_source):
        filter_by = {"source": source, "upvote_count": {"$exists": True}}
        if child_source is not None:
            filter_by['child_source'] = child_source
        return self.db.images.find(filter_by)

    def update_facebook_page_activity(self, page_id, last_updated):
        return self.db.facebook.update({"id": page_id}, {"$set": {"last_crawled": last_updated}},
                                       upsert=False)

    def update_twitter_activity(self, handle, last_updated):
        return self.db.twitter.update({"screen_name": handle}, {"$set": {"last_crawled": last_updated}},
                                      upsert=False)
