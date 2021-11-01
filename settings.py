import os

import dj_redis_url

MONGODB_URL = 'mongodb://localhost:27017/'
MONGODB_NAME = 'meme_id'

MAX_PAGE = 10
NINE_GAG_FREQ = 10

EXCLUDED_TLDS = ["ru", "pl", "de", "ms", "sk", "gov", "nl", "dk", "gov", "es", "cn", "fi", "pt", "gr", "in", "tv", "rs",
                 "mil", "fr", "istanbul", "ca", "ua", "me", "it", "jp", "hu", "su", "se", "biz", "ir", "ch",
                 "kr", "info", "eu", "th", "co", "mg", "vn", "is", "news", "cc", "ag", "video", "cz", "bg", "ie", "at",
                 "by", "ga", "ws", "id", "chat", "moe", "lt", "nu", "asia", "kz", "hk", "ma", "ro"]
EXCLUDED_TLDS += [u'cy', u'cl', u'io', u'today', u'cu', u're', u'photos', u'hr', u'be', u'team', u'ng', u'az', u'gift',
                  u'global', u'no', u'mo', u'uz', u'review', u'tr', u'si', u'ee', u'to', u'pro', u'wang', u'site',
                  u'bo', u'au', u'ar', u'gg', u'pe', u'st', u'club', u'edu', u'sg', u'degree', u'kim', u'bz', u'my',
                  u'am', u'ink', u'world', u'im', u'fun', u'black', u'tokyo', u'gt', u'sl', u'ml', u'la', u'lv', u'cat',
                  u'nz', u'cd', u'tj', u'tw', u'164', u'li', u'za', u'il', u'mk', u'ph', u'gs', u'kr:8443',
                  u'%D1%80%D1%84', u'br', u'live', u'mx', u'farm', u'uk', u'guru', u'name', u'cr', u'md', u'33', u'xxx',
                  u'pub', u'mu', u'ovh', u'mobi', u'lk', u'kg', u'press', u'tk', u'systems', u'do', u'so', u'fm',
                  u'life', u'mn', u'hn', u'me:9100', u'wiki', u'uy', u'blog', u'top', u'space', u'vg', u'works',
                  u'watch', u'ai', u'al', u'zone', u'net:45680', u'71', u'cx', u'tt', u'fo', u'ec', u'men', u'football',
                  u'win', u'187', u'education', u'cm', u'hiphop', u'ninja', u'sh', u'app', u'37', u'vn:9002', u'ba',
                  u'land', u'earth', u'pw', u'245', u'lu', u'design', u'network', u'pk', u'ge', u'marketing', u'travel',
                  u'store', u'academy', u'tn', u'family', u'tz', u'es:83', u'101', u'link', u'town', u'download', u'ly',
                  u'ke', u'np', u'observer', u'tips', u'com:81', u'79', u'gy', u'sexy', u'mt', u'mm', u'science', u'ps',
                  u'250:6025', u'games', u'work', u'auction', u'audio', u'vip', u'show', u'sa', u'help', u'love',
                  u'party', u'domains', u'cloud', u'training', u'kw', u'89', u'shop', u'porn', u'35', u'ni', u'swiss',
                  u'22', u'135', u'cafe', u'ooo', u'guide', u'icu', u'132', u'eg', u'pet', u'host', u'gh', u'green',
                  u'com:7861', u'lb', u'dog', u'as', u'pm', u'agency', u'tech', u'aero', u'one', u'sv', u'nyc', u'tc',
                  u'pw:81', u'py', u'pa', u'edu:8080', u'photo', u'nagoya', u'249', u'fj', u'pics', u'183', u'soy',
                  u'bh', u'gq', u'177', u'ae', u'coop', u'us:81', u'click', u'london', u'events', u've', u'city', u'65',
                  u'62', u'119', u'plus', u'art', u'228', u'eus', u'date', u'codes', u'73', u'com:8080',
                  u'%E4%B8%AD%E5%9B%BD', u'cf', u'berlin', u'onl', u'dz', u'99', u'digital', u'hm', u'support', u'vc',
                  u'gallery', u'81', u'ventures', u'23', u'direct', u'gdn', u'bd', u'school', u'gal', u'builders',
                  u'bo:81', u'expert', u'company', u'vn:8080', u'int', u'krd', u'151', u'citic', u'miami', u'sc']

WS4REDIS_EXPIRE = 8

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
REDIS_CONNECTION = dj_redis_url.parse(REDIS_URL)

WS4REDIS_HEARTBEAT = 1
# WS4REDIS_EXPIRE = 100
WS4REDIS_PREFIX = 'ws'
WEBSOCKET_URL = '/ws/'

WS4REDIS_CONNECTION = {
    'host': REDIS_CONNECTION['HOST'],
    'port': REDIS_CONNECTION['PORT'],
    'db': REDIS_CONNECTION['DB'],
    'password': REDIS_CONNECTION['PASSWORD']
}

TUMBLR_OAUTH_KEY = ''
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
REDDIT_CLIENT_SECRET = ''
REDDIT_CLIENT_ID = ''
REDDIT_PASSWORD = ''
REDDIT_USERNAME = ''

TWITTER_API_KEY = ''
TWITTER_API_SECRET = ''
TWITTER_ACCESS_TOKEN = ''
TWITTER_ACCESS_TOKEN_SECRET = ''

FACEBOOK_ACCESS_TOKEN = ''
BEGIN_CRAWL_SINCE = 1553065200
TEXT_SIMILARITY_THRESHOLD = 0.9
UTC_HOUR_DIFF = 7
PINTEREST_APP_ID = ''
PINTEREST_APP_SECRET = ''
PINTEREST_EMAIL = ''
PINTEREST_PWD = ''
FACEBOOK_TIMEOUT = 18

DATA_ROOT_PATH = ''
CRAWL_DAYS_BACK = 2

GOOGLE_CLOUD_CREDENTIALS_FILE = ""
try:
    from local_settings import *
except:
    print("local_settings.py not found.")
