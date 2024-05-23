# This file is part of the MapProxy project.
# Copyright (C) 2017 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import hashlib
import datetime
import time
from io import BytesIO

from mapproxy.image import ImageSource
from mapproxy.cache.base import (
    TileCacheBase,
    tile_buffer,
)

try:
    import redis
except ImportError:
    redis = None


import logging
log = logging.getLogger(__name__)


class RedisBaseCache(TileCacheBase):
    def __init__(self, host, port, prefix, r, ttl=0, db=0, coverage=None):
        super(RedisBaseCache, self).__init__(coverage)

        if redis is None:
            raise ImportError("Redis backend requires 'redis' package.")
        md5 = (
            "redis-"
            + hashlib.new(
                "md5",
                (host + str(port) + prefix + str(db)).encode("utf-8"),
                usedforsecurity=False,
            ).hexdigest()
        )
        self.prefix = prefix
        self.lock_cache_id = md5
        self.ttl = ttl
        self.r = r

    def _key(self, tile):
        x, y, z = tile.coord
        return self.prefix + '-%d-%d-%d' % (z, x, y)

    def is_cached(self, tile, dimensions=None):
        if tile.coord is None or tile.source:
            return True
        key = self._key(tile)

        try:
            log.debug('exists_key, key: %s' % key)
            return self.r.exists(key)
        except redis.exceptions.ConnectionError as e:
            log.error('Error during connection %s' % e)
            return False
        except Exception as e:
            log.error('REDIS:exists_key error  %s' % e)
            return False

    def store_tile(self, tile, dimensions=None):
        if tile.stored:
            return True
        key = self._key(tile)

        with tile_buffer(tile) as buf:
            data = buf.read()

        try:
            log.debug('store_key, key: %s' % key)
            r = self.r.set(key, data)
        except redis.exceptions.ConnectionError as e:
            log.error('Error during connection %s' % e)
            return False
        except Exception as e:
            log.error('REDIS:store_key error  %s' % e)
            return False

        if self.ttl:
            # use ms expire times for unit-tests
            self.r.pexpire(key, int(self.ttl * 1000))
        return r

    def load_tile_metadata(self, tile, dimensions=None):
        if tile.timestamp:
            return
        pipe = self.r.pipeline()
        pipe.ttl(self._key(tile))
        pipe.memory_usage(self._key(tile))
        pipe_res = pipe.execute()
        tile.timestamp = time.mktime(datetime.datetime.now().timetuple()) - self.ttl - int(pipe_res[0])
        tile.size = pipe_res[1]

    def load_tile(self, tile, with_metadata=False, dimensions=None):
        if tile.source or tile.coord is None:
            return True
        key = self._key(tile)

        try:
            log.debug('get_key, key: %s' % key)
            tile_data = self.r.get(key)
            if tile_data:
                tile.source = ImageSource(BytesIO(tile_data))
                return True
            return False
        except redis.exceptions.ConnectionError as e:
            log.error('Error during connection %s' % e)
            return False
        except Exception as e:
            log.error('REDIS:get_key error  %s' % e)
            return False

    def remove_tile(self, tile, dimensions=None):
        if tile.coord is None:
            return True

        key = self._key(tile)
        self.r.delete(key)
        return True


class RedisCache(RedisBaseCache):
    def __init__(
        self,
        host,
        port,
        prefix,
        ttl=0,
        db=0,
        username=None,
        password=None,
        coverage=None,
        ssl_certfile=None,
        ssl_keyfile=None,
        ssl_ca_certs=None,
    ):
        super(RedisCache, self).__init__(
            host,
            port,
            prefix,
            redis.StrictRedis(
                host=host,
                port=port,
                username=username,
                password=password,
                db=db,
                ssl_certfile=ssl_certfile,
                ssl_keyfile=ssl_keyfile,
                ssl_ca_certs=ssl_ca_certs,
                ssl=all([ssl_certfile, ssl_keyfile]),
            ),
            ttl=ttl,
            db=db,
            coverage=coverage,
        )


class RedisClusterCache(RedisBaseCache):
    def __init__(
        self,
        host,
        port,
        prefix,
        ttl=0,
        db=0,
        username=None,
        password=None,
        coverage=None,
        ssl_certfile=None,
        ssl_keyfile=None,
        ssl_ca_certs=None,
    ):
        super(RedisClusterCache, self).__init__(
            host,
            port,
            prefix,
            redis.RedisCluster(
                host=host,
                port=port,
                username=username,
                password=password,
                ssl_certfile=ssl_certfile,
                ssl_keyfile=ssl_keyfile,
                ssl_ca_certs=ssl_ca_certs,
                ssl=all([ssl_certfile, ssl_keyfile]),
            ),
            ttl=ttl,
            db=db,
            coverage=coverage,
        )
