import basc_py4chan
import time
from crawlers.generic import BaseCrawler
from settings import BEGIN_CRAWL_SINCE


class FourChanCrawler(BaseCrawler):

    def __init__(self, boards, *args, **kwargs):
        super(FourChanCrawler, self).__init__(source='four_chan', *args, **kwargs)
        self.url = 'https://www.4chan.com/{}/'
        self.boards = boards
        self.timeout = 16

    def get_feed(self, board_name):
        images = []
        board = basc_py4chan.Board(board_name)
        all_thread_ids = board.get_all_thread_ids()
        for t in all_thread_ids:
            thread = board.get_thread(t)
            if thread is None:
                continue
            topic = thread.topic
            ts = topic.timestamp
            for f in thread.file_objects():
                try:
                    img_id = "{}_{}".format(topic.post_number, f.filename.split('.')[0])
                    images.append({
                        "created_at": ts,
                        "id": img_id,
                        "image_url": f.file_url
                    })
                except:
                    pass
            time.sleep(0.1)

        return images

    def _pre_process_data(self, board_name, data):
        results = []
        for e in data:
            try:

                if e['created_at'] >= BEGIN_CRAWL_SINCE:
                    results.append(
                        {
                            "id": e.get('id'),
                            "image_url": e.get("image_url"),
                            "file_name": 'data/{}/{}/{}.jpg'.format(self.source, board_name, e['id']),
                            "source": self.source,
                            "created_at": e.get("created_at"),
                            "child_source": board_name
                        }
                    )
            except:
                print("four_chan {} failed to preprocess data".format(board_name))
        return results

    def run(self):
        self._log_console("Starting up {} crawler ...".format(self.source))
        self._create_mongo_db_connection()
        while self.running:
            try:
                for board in self.boards:
                    data = self.get_feed(board)
                    pre_processed_data = self._pre_process_data(board, data)
                    self.process_data(pre_processed_data)
                    time.sleep(self.timeout)
                    self._log_console("Iteration ended with {} items...".format(len(pre_processed_data)))
                time.sleep(60)
            except Exception as e:
                print(e)
                self._log_console("Exception on main thread run()")
