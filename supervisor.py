import os
import signal
import threading
from Queue import Queue

from urlparse import urlparse

import requests
from google.cloud import vision
from pymongo import MongoClient

from crawlers.buzzfeed import BuzzFeedCrawler
from crawlers.cheez_burger import CheezBurgerCrawler
from crawlers.dopl3r import Dopl3rCrawler
from crawlers.dump_a_day import DumpADayCrawler
from crawlers.funny_memes import FunnyMemesCrawler
from crawlers.funnyjunk import FunnyJunkCrawler
from crawlers.ifunny import IfunnyCrawler
from crawlers.imgflip import ImgFlipCrawler
from crawlers.imgur import ImgurCrawler
from crawlers.instagram import InstagramCrawler
from crawlers.ladnow import LadnowCrawler
from crawlers.le_funny import LeFunnyCrawler
from crawlers.me_me import MeMeCrawler
from crawlers.meme_generator import MemeGeneratorCrawler
from crawlers.meme_guy import MemeGuyCrawler
from crawlers.meme_xyz import MemeXYZCrawler
from crawlers.memedroid import MemedroidCrawler
from crawlers.nine_gag import NineGagCrawler
from crawlers.on_sizzle import OnSizzleCrawler
from crawlers.pinterest_crawler import PinterestCrawler
from crawlers.quora_treasury import QuoraTreasuryCrawler
from crawlers.reddit import RedditCrawler, r_get_submission_comments
from crawlers.ruin_my_week import RuinMyWeekCrawler
from crawlers.the_chive import TheChiveCrawler
from crawlers.the_funny_beaver import TheFunnyBeaverCrawler
from crawlers.the_humor_train import TheHumorTrainCrawler
from crawlers.troll_street import TrollStreetCrawler
from crawlers.tumblr import TumblrCrawler
from crawlers.vifunow import VifunowCrawler
from crawlers.dank_meme_team import DankMemeTeamCrawler
from crawlers.funny_photo import FunnyPhotoCrawler
from crawlers.img_lulz import ImgLulzCrawler
from crawlers.huge_lol import HugeLolCrawler
from crawlers.daily_pic_dump import DailyPicDumpCrawler
from crawlers.call_center_memes import CallCenterMemesCrawler
from crawlers.pr0gramm import Pr0grammCrawler
from crawlers.trend_uso import TrendUSOMemesCrawler
from crawlers.best_funny_pic import BestFunnyPicCrawler
from crawlers.joy_reactor import JoyReactorCrawler
from crawlers.beer_money_pizza import BeerMoneyPizzaCrawler
from crawlers.hidden_lol import HiddenLolCrawler
from crawlers.fun_substance import FreshSubstanceCrawler
from crawlers.nine_buzz import NineBuzzCrawler
from crawlers.the_meta_picture import TheMetaPictureCrawler
from crawlers.daily_haha import DailyHahaCrawler
from crawlers.dev_humor import DevHumorCrawler
from crawlers.iwsmt import IWSMTCrawler
from crawlers.four_pm_happy_hour import FourPMHappyHourCrawler
from crawlers.kontraband import KontrabandCrawler
from crawlers.still_cracking import StillCrackingCrawler
from crawlers.meme_collection import MemeCollectionCrawler
from crawlers.slow_robot import SlowRobotCrawler
from crawlers.wanna_joke import WannaJokeCrawler
from crawlers.some_ecards import SomeEcardsCrawler
from crawlers.laugh_tard import LaughTardCrawler
from crawlers.humour_spot import HumourSpotCrawler
from crawlers.put_me_like import PutMeLikeCrawler
from crawlers.spastic_bastard import SpasticBastardCrawler
from crawlers.saying_images import SayingImagesCrawler
from crawlers.fun_pic import FunPicCrawler
from crawlers.barnorama import BarnoramaCrawler
from crawlers.fun_mary import FunMaryCrawler
from crawlers.gorilla_feed import GorillaFeedCrawler
from crawlers.one_jux import OneJuxCrawler
from crawlers.odd_stuff_magazine import OddStuffMagazineCrawler
from crawlers.love_for_quotes import LoveForQuotesCrawler
from crawlers.bored_panda import BoredPandaCrawler
from crawlers.ebaums_world import EbaumsWorldCrawler
from crawlers.thunder_dungeon import ThunderDungeonCrawler
from crawlers.zodab import ZodabCrawler
from crawlers.funny_captions import FunnyCaptionsCrawler
from crawlers.fame_pace import FamePaceCrawler
from crawlers.funny_memes_4u import FunnyMemes4UCrawler
from crawlers.epic_pix import EpicPixCrawler
from crawlers.lol_damn import LolDamnCrawler
from crawlers.uber_humor import UberHumorCrawler
from crawlers.just_viral import JustViralCrawler
from crawlers.acid_cow import AcidCowCrawler
from crawlers.facebook_crawler import FacebookCrawler
from crawlers.four_chan import FourChanCrawler
from crawlers.clean_memes import CleanMemesCrawler
from crawlers.the_last_thing_99 import TheLastThingCrawler
from crawlers.astrology_memes import AstrologyMemesCrawler
from crawlers.thuglife_meme import ThugLifeMemeCrawler
from crawlers.izismile import IzismileCrawler
from crawlers.quotes_n_humor import QuotesNHumorCrawler
from crawlers.screen_eggs import ScreenEggsCrawler
from crawlers.twitter_crawler import TwitterCrawler

# from crawlers.evil_milk import EvilMilkCrawler

from settings import EXCLUDED_TLDS, CRAWL_DAYS_BACK, DATA_ROOT_PATH, BEGIN_CRAWL_SINCE, \
    MONGODB_NAME
from utils import sha256_checksum, annotate_text, annotate_web

google_client = vision.ImageAnnotatorClient()
mongo_client = MongoClient()
db = mongo_client[MONGODB_NAME]
posts = db.posts
instagram = db.instagram
instagram_nodes = db.instagram_nodes
nine_gag = db.nine_gag
reddit = db.reddit
imgur = db.imgur
imgflip = db.imgflip
funny_junk = db.funny_junk
on_sizzle = db.on_sizzle

routes = db.routes
images = db.images
sources = db.sources
facebook_pages = db.facebook
twitter_accounts = db.twitter

google_queue = Queue()

CRAWLER_THREADS = {}


def get_http_headers(url):
    response = requests.get(url)
    if response.status_code == 404:
        return None
    return response.headers


ig_accounts = sorted([r.lower() for r in sources.find_one({"name": "instagram"})['children']])
four_chan_boards = ['b', 'pol']

sub_reddit_accounts = [r.lower() for r in sources.find_one({"name": "reddit"})['children']]
facebook_pages_list = [p for p in facebook_pages.find({"posts": {"$exists": True}, "deleted": {"$exists": False},
                                                       "latest_post_time": {"$gte": "2019-01-01T08:00:20+0000"}}).sort(
    "last_crawled", 1)]

twitter_accounts_list = [p for p in twitter_accounts.find({"deleted": {"$exists": False}}).sort("last_crawled", 1)]
for i in ig_accounts:
    if not os.path.exists("{}/data/instagram/{}".format(DATA_ROOT_PATH, i)):
        os.mkdir("{}/data/instagram/{}".format(DATA_ROOT_PATH, i))
for p in facebook_pages_list:
    if not os.path.exists("{}/data/facebook/{}".format(DATA_ROOT_PATH, p['id'])):
        os.mkdir("{}/data/facebook/{}".format(DATA_ROOT_PATH, p['id']))

for p in twitter_accounts_list:
    if not os.path.exists("{}/data/twitter/{}".format(DATA_ROOT_PATH, p['screen_name'])):
        os.mkdir("{}/data/twitter/{}".format(DATA_ROOT_PATH, p['screen_name']))

for b in four_chan_boards:
    if not os.path.exists("{}/data/four_chan/{}".format(DATA_ROOT_PATH, b)):
        os.mkdir("{}/data/four_chan/{}".format(DATA_ROOT_PATH, b))


def get_text_regions(filename):
    annotations = annotate_text(google_client, filename)
    text_regions = []
    for a in annotations:
        t = {'description': a.description, 'locale': a.locale}
        poly = []
        for v in a.bounding_poly.vertices:
            poly.append({"x": v.x, "y": v.y})

        t['bounding_poly'] = poly
        text_regions.append(t)
    return text_regions


def get_web_detection(filename):
    annotations = annotate_web(google_client, filename)
    full_matching_images = []
    pages_with_matching_images = []
    if annotations.full_matching_images:
        for a in annotations.full_matching_images:
            full_matching_images.append({"url": a.url, "score": a.score})
    if annotations.pages_with_matching_images:
        for a in annotations.pages_with_matching_images:
            pages_with_matching_images.append(
                {"url": a.url, "page_tile": a.page_title})
    return full_matching_images, pages_with_matching_images


def _vision_thread():
    while True:
        img = google_queue.get()
        if img is None:
            break
        img_obj = images.find_one({"_id": img["_id"]})
        file_name = os.path.join(DATA_ROOT_PATH, img_obj['file_name'])
        try:
            file_stat = os.stat(file_name)
            if file_stat.st_size > 10485759:
                continue
            if img_obj[
                'created_at'] < BEGIN_CRAWL_SINCE:  # (int(time.time()) - timedelta(days=CRAWL_DAYS_BACK).total_seconds()):
                continue
            if 'text_regions' in img_obj:
                print("Skipping {}".format(file_name))
                continue

            if os.path.exists(file_name):
                print("Text for {}".format(file_name))
                print('-' * 64)
                try:
                    img_obj['text_regions'] = get_text_regions(file_name)
                    img_obj['full_matching_images'], img_obj['pages_with_matching_images'] = get_web_detection(
                        file_name)
                    if len(img_obj['text_regions']):
                        img_obj["text"] = img_obj['text_regions'][0]['description']
                    img_obj['google_query_completed'] = True
                except Exception as ex:
                    print(ex)
                    print('[ERROR]: {}'.format(file_name))
            else:
                print("{} not found".format(file_name))
            images.update_one({'_id': img_obj['_id']}, {"$set": img_obj}, upsert=False)
            print('-' * 82)
        except Exception as ex:
            print(ex)
            print("[{}] failed ...///{}".format(img_obj['source'], file_name))

def signal_handler(signum, frame):
    if signum in [signal.SIGINT]:
        sources.update_many({"is_verified": True}, {"$set": {"is_running": False}}, upsert=False)
        print("[supervisor.py] Stop signal received, waiting for children to terminate")
    exit(0)


tumblr_blogs = [
    u'paxamericana.tumblr.com', u'cartoon-dog.tumblr.com',
    u'dragondicks.tumblr.com', u'terriamon.tumblr.com',
    u'thisiselliz.tumblr.com', u'wonder-mechanic.tumblr.com',
    'buzzfeed.tumblr.com', u'memearchives.tumblr.com', 'tomche.tumblr.com',
    'h-i-l-a-r-i-o-u-s.tumblr.com', 'funnygamememes.tumblr.com', 'omg-humor.com', 'srsfunny.net',
    'memes.tumblr.com', 'killowave-the-2nd.tumblr.com', 'memes--memes.tumblr.com', 'hedankest.tumblr.com',
    'the-memedaddy.tumblr.com', 'dankmemesreasonforliving.tumblr.com', 'lolwtfmemes.tumblr.com',
    'knowwhatime.me', 'thatgirlwiththememes.tumblr.com', 'kpop-memess.tumblr.com', 'fakehistory.tumblr.com',
    'funny.directory', 'edgy-memes-for-woke-teens.tumblr.com', 'universeofmemes.tumblr.com',
    'unpredictablememes.tumblr.com', '30-minute-memes.tumblr.com', 'memecollege.tumblr.com',
    'tumblr.tastefullyoffensive.com', 'meme-fire.tumblr.com', 'im-sad-and-i-like-memes.tumblr.com',
    'forthefuns.tumblr.com', 'thesoberbitch.tumblr.com', 'memeosas.tumblr.com', 'memes-r-memes.tumblr.com',
    'spicymemesociety.tumblr.com', 'catchymemes.com', 'memeuplift.tumblr.com', 'the-suburban-craft.tumblr.com',
    'annoyingmemes.tumblr.com', 'omghotmemes.tumblr.com', 'forever-memes.tumblr.com', 'thatfunnymeme.tumblr.com',
    'memelord18.tumblr.com', 'xno-chill-memesx.tumblr.com', 'lobotomizedbrain.tumblr.com', 'meme-gutter.tumblr.com',
    'sassysaidie.tumblr.com', 'browsedankmemes.com'
]

if __name__ == '__main__':
    signal.signal(signal.SIGCHLD, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    srs = [sub_reddit.replace('r/', '') for sub_reddit in sub_reddit_accounts]
    nine_proc = NineGagCrawler(google_queue=google_queue)
    fj_proc = FunnyJunkCrawler(google_queue=google_queue)
    on_sizzle_proc = OnSizzleCrawler(google_queue=google_queue)
    imgflip_proc = ImgFlipCrawler(google_queue=google_queue)
    imgur_proc = ImgurCrawler(google_queue=google_queue)
    meme_xyz_proc = MemeXYZCrawler(google_queue=google_queue)
    meme_proc = MeMeCrawler(google_queue=google_queue)
    memedroid_proc = MemedroidCrawler(google_queue=google_queue)
    vifunow_proc = VifunowCrawler(google_queue=google_queue)
    quora_treasury_proc = QuoraTreasuryCrawler(google_queue=google_queue)
    cheez_burger_proc = CheezBurgerCrawler(google_queue=google_queue)
    the_chive_proc = TheChiveCrawler(google_queue=google_queue)
    ruin_my_week_proc = RuinMyWeekCrawler(google_queue=google_queue)
    dump_a_day_proc = DumpADayCrawler(google_queue=google_queue)
    troll_street_proc = TrollStreetCrawler(google_queue=google_queue)
    the_humor_train_proc = TheHumorTrainCrawler(google_queue=google_queue)
    ifunny_proc = IfunnyCrawler(google_queue=google_queue)
    ladnow_proc = LadnowCrawler(google_queue=google_queue)
    meme_generator_proc = MemeGeneratorCrawler(google_queue=google_queue)
    buzzfeed_proc = BuzzFeedCrawler(google_queue=google_queue)
    meme_guy_proc = MemeGuyCrawler(google_queue=google_queue)
    dopl3r_proc = Dopl3rCrawler(google_queue=google_queue)
    the_funny_beaver_proc = TheFunnyBeaverCrawler(google_queue=google_queue)
    funny_memes_proc = FunnyMemesCrawler(google_queue=google_queue)
    le_funny_proc = LeFunnyCrawler(google_queue=google_queue)
    dank_meme_team = DankMemeTeamCrawler(google_queue=google_queue)
    funny_photo = FunnyPhotoCrawler(google_queue=google_queue)
    img_lulz = ImgLulzCrawler(google_queue=google_queue)
    huge_lol = HugeLolCrawler(google_queue=google_queue)
    daily_pic_dump = DailyPicDumpCrawler(google_queue=google_queue)
    call_center_memes = CallCenterMemesCrawler(google_queue=google_queue)
    pr0gramm_crawler = Pr0grammCrawler(google_queue=google_queue)
    trend_uso_crawler = TrendUSOMemesCrawler(google_queue=google_queue)
    best_funny_pic_crawler = BestFunnyPicCrawler(google_queue=google_queue)
    joy_reactor_crawler = JoyReactorCrawler(google_queue=google_queue)
    beer_money_pizza_crawler = BeerMoneyPizzaCrawler(google_queue=google_queue)
    hidden_lol_crawler = HiddenLolCrawler(google_queue=google_queue)
    fun_substance_crawler = FreshSubstanceCrawler(google_queue=google_queue)
    nine_buzz_crawler = NineBuzzCrawler(google_queue=google_queue)
    the_meta_picture_crawler = TheMetaPictureCrawler(google_queue=google_queue)
    daily_haha_crawler = DailyHahaCrawler(google_queue=google_queue)
    dev_humor_crawler = DevHumorCrawler(google_queue=google_queue)
    iwsmt_crawler = IWSMTCrawler(google_queue=google_queue)
    four_pm_happy_hour_crawler = FourPMHappyHourCrawler(google_queue=google_queue)
    kontraband_crawler = KontrabandCrawler(google_queue=google_queue)
    still_cracking_crawler = StillCrackingCrawler(google_queue=google_queue)
    meme_collection_crawler = MemeCollectionCrawler(google_queue=google_queue)
    slow_robot_crawler = SlowRobotCrawler(google_queue=google_queue)
    wanna_joke_crawler = WannaJokeCrawler(google_queue=google_queue)
    some_ecards_crawler = SomeEcardsCrawler(google_queue=google_queue)
    laugh_tard_crawler = LaughTardCrawler(google_queue=google_queue)
    humour_spot_crawler = HumourSpotCrawler(google_queue=google_queue)
    put_me_like_crawler = PutMeLikeCrawler(google_queue=google_queue)
    spastic_bastard_crawler = SpasticBastardCrawler(google_queue=google_queue)
    saying_images_crawler = SayingImagesCrawler(google_queue=google_queue)
    fun_pic_crawler = FunPicCrawler(google_queue=google_queue)
    barnorama_crawler = BarnoramaCrawler(google_queue=google_queue)
    fun_mary_crawler = FunMaryCrawler(google_queue=google_queue)
    gorilla_feed_crawler = GorillaFeedCrawler(google_queue=google_queue)
    one_jux_crawler = OneJuxCrawler(google_queue=google_queue)
    odd_stuff_magazine_crawler = OddStuffMagazineCrawler(google_queue=google_queue)
    love_for_quotes_crawler = LoveForQuotesCrawler(google_queue=google_queue)
    bored_panda_crawler = BoredPandaCrawler(google_queue=google_queue)
    ebaums_world_crawler = EbaumsWorldCrawler(google_queue=google_queue)
    thunder_dungeon_crawler = ThunderDungeonCrawler(google_queue=google_queue)
    zodab_crawler = ZodabCrawler(google_queue=google_queue)
    funny_captions_crawler = FunnyCaptionsCrawler(google_queue=google_queue)
    fame_pace_crawler = FamePaceCrawler(google_queue=google_queue)
    funny_memes_4u_crawler = FunnyMemes4UCrawler(google_queue=google_queue)
    epic_pix_crawler = EpicPixCrawler(google_queue=google_queue)
    lol_damn_crawler = LolDamnCrawler(google_queue=google_queue)
    uber_humor_crawler = UberHumorCrawler(google_queue=google_queue)
    just_viral_crawler = JustViralCrawler(google_queue=google_queue)
    acid_cow_crawler = AcidCowCrawler(google_queue=google_queue)
    clean_memes_crawler = CleanMemesCrawler(google_queue=google_queue)
    the_last_thing_crawler = TheLastThingCrawler(google_queue=google_queue)
    astrology_memes_crawler = AstrologyMemesCrawler(google_queue=google_queue)
    thug_life_meme_crawler = ThugLifeMemeCrawler(google_queue=google_queue)
    # evil_milk_crawler = EvilMilkCrawler(google_queue=google_queue) --not meme
    reddit_thread = RedditCrawler(sub_reddits=srs, google_queue=google_queue)
    ig_thread = InstagramCrawler(handles=ig_accounts, google_queue=google_queue)
    tumblr_thread = TumblrCrawler(blogs=tumblr_blogs, google_queue=google_queue)
    four_chan_thread = FourChanCrawler(boards=four_chan_boards, google_queue=google_queue)
    facebook_thread = FacebookCrawler(pages=facebook_pages_list, google_queue=google_queue)
    twitter_thread = TwitterCrawler(handles=twitter_accounts_list, google_queue=google_queue)

    izismile_crawler = IzismileCrawler(google_queue=google_queue)
    quotes_n_humor_crawler = QuotesNHumorCrawler(google_queue=google_queue)
    screen_eggs_crawler = ScreenEggsCrawler(google_queue=google_queue)

    collect_new_data = True
    for x in range(0, 8):
        google_vision_thread = threading.Thread(target=_vision_thread)
        google_vision_thread.start()

    if collect_new_data:
        fj_proc.start()
        nine_proc.start()
        on_sizzle_proc.start()
        imgflip_proc.start()
        imgur_proc.start()
        meme_xyz_proc.start()
        memedroid_proc.start()
        vifunow_proc.start()
        # quora_treasury_proc.start() #offline
        cheez_burger_proc.start()
        the_chive_proc.start()
        ruin_my_week_proc.start()
        dump_a_day_proc.start()
        troll_street_proc.start()
        the_humor_train_proc.start()
        ifunny_proc.start()
        meme_generator_proc.start()
        buzzfeed_proc.start()
        meme_guy_proc.start()
        dopl3r_proc.start()
        the_funny_beaver_proc.start()
        # funny_memes_proc.start()
        le_funny_proc.start()
        dank_meme_team.start()
        funny_photo.start()
        img_lulz.start()
        huge_lol.start()
        daily_pic_dump.start()
        call_center_memes.start()
        pr0gramm_crawler.start()
        trend_uso_crawler.start()
        best_funny_pic_crawler.start()
        joy_reactor_crawler.start()
        beer_money_pizza_crawler.start()
        hidden_lol_crawler.start()
        fun_substance_crawler.start()
        nine_buzz_crawler.start()
        the_meta_picture_crawler.start()
        daily_haha_crawler.start()
        dev_humor_crawler.start()
        iwsmt_crawler.start()
        four_pm_happy_hour_crawler.start()
        kontraband_crawler.start()
        still_cracking_crawler.start()
        meme_collection_crawler.start()
        slow_robot_crawler.start()
        wanna_joke_crawler.start()
        some_ecards_crawler.start()
        laugh_tard_crawler.start()
        humour_spot_crawler.start()
        put_me_like_crawler.start()
        spastic_bastard_crawler.start()
        saying_images_crawler.start()
        fun_pic_crawler.start()
        barnorama_crawler.start()
        fun_mary_crawler.start()
        gorilla_feed_crawler.start()
        one_jux_crawler.start()
        odd_stuff_magazine_crawler.start()
        love_for_quotes_crawler.start()
        bored_panda_crawler.start()
        ebaums_world_crawler.start()
        thunder_dungeon_crawler.start()
        zodab_crawler.start()
        funny_captions_crawler.start()
        fame_pace_crawler.start()
        # funny_memes_4u_crawler.start()
        epic_pix_crawler.start()
        lol_damn_crawler.start()
        uber_humor_crawler.start()
        just_viral_crawler.start()
        acid_cow_crawler.start()
        # evil_milk_crawler.start()
        clean_memes_crawler.start()
        the_last_thing_crawler.start()
        astrology_memes_crawler.start()
        thug_life_meme_crawler.start()

        facebook_thread.start()
        four_chan_thread.start()
        reddit_thread.start()
        ig_thread.start()
        tumblr_thread.start()
        twitter_thread.start()

        izismile_crawler.start()
        quotes_n_humor_crawler.start()
        screen_eggs_crawler.start()

    print("Sig Pause..")
    signal.pause()
