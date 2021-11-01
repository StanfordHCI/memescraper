import hashlib
import io
import os

import six

import settings

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_CLOUD_CREDENTIALS_FILE

from google.cloud.vision import types
from redis import ConnectionPool, StrictRedis

redis_connection_pool = ConnectionPool(**settings.WS4REDIS_CONNECTION)


def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


def annotate_text(client, file_name):
    f = os.path.join(
        os.path.dirname(__file__), file_name)
    with io.open(f, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)
    response = client.text_detection(image=image)
    return response.text_annotations


def annotate_web(client, file_name):
    f = os.path.join(
        os.path.dirname(__file__), file_name)
    with io.open(f, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)
    response = client.web_detection(image=image)
    return response.web_detection


def detect_safe_search(client, url):
    image = types.Image()
    image.source.image_uri = url
    response = client.safe_search_detection(image=image)
    return response.safe_search_annotation


class RedisMessage(six.binary_type):
    """
    A class wrapping messages to be send and received through RedisStore. This class behaves like
    a normal string class, but silently discards heartbeats and converts messages received from
    Redis.
    """

    def __new__(cls, value):
        if six.PY3:
            if isinstance(value, str):
                if value != settings.WS4REDIS_HEARTBEAT:
                    value = value.encode()
                    return super(RedisMessage, cls).__new__(cls, value)
            elif isinstance(value, bytes):
                if settings.WS4REDIS_HEARTBEAT is None or value != settings.WS4REDIS_HEARTBEAT.encode():
                    return super(RedisMessage, cls).__new__(cls, value)
            elif isinstance(value, list):
                if len(value) >= 2 and value[0] == b'message':
                    return super(RedisMessage, cls).__new__(cls, value[2])
        else:
            if isinstance(value, six.string_types):
                if value != settings.WS4REDIS_HEARTBEAT:
                    return six.binary_type.__new__(cls, value)
            elif isinstance(value, list):
                if len(value) >= 2 and value[0] == 'message':
                    return six.binary_type.__new__(cls, value[2])
        return None


class RedisStore(object):
    """
    Abstract base class to control publishing and subscription for messages to and from the Redis
    datastore.
    """
    _expire = settings.WS4REDIS_EXPIRE

    def __init__(self, connection):
        self._connection = connection
        self._publishers = set()

    def publish_message(self, message, expire=None):
        """
        Publish a ``message`` on the subscribed channel on the Redis datastore.
        ``expire`` sets the time in seconds, on how long the message shall additionally of being
        published, also be persisted in the Redis datastore. If unset, it defaults to the
        configuration settings ``WS4REDIS_EXPIRE``.

        dmorina: Ported from django-redis-websockets, only supports broadcasts
        """
        if expire is None:
            expire = self._expire
        if not isinstance(message, RedisMessage):
            raise ValueError('message object is not of type RedisMessage')
        for channel in self._publishers:
            self._connection.publish(channel, message)
            if expire > 0:
                self._connection.setex(channel, expire, message)

    @staticmethod
    def get_prefix():
        return settings.WS4REDIS_PREFIX and '{0}:'.format(settings.WS4REDIS_PREFIX) or ''

    def _get_message_channels(self, request=None, facility='{facility}', broadcast=False,
                              groups=(), users=(), sessions=()):
        prefix = self.get_prefix()
        channels = []
        if broadcast is True:
            channels.append('{prefix}broadcast:{facility}'.format(prefix=prefix, facility=facility))
        return channels


class RedisPublisher(RedisStore):
    def __init__(self, **kwargs):
        """
        Initialize the channels for publishing messages through the message queue.
        """
        self.connection = StrictRedis(connection_pool=redis_connection_pool)
        super(RedisPublisher, self).__init__(self.connection)
        for key in self._get_message_channels(**kwargs):
            self._publishers.add(key)

    @staticmethod
    def stop():
        redis_connection_pool.disconnect()

# def get_hashid(id_int):
#     hash_id = Hashids(salt=settings.HASHIDS_SECRET_KEY, min_length=8)
#     return hash_id.encode(id_int)
