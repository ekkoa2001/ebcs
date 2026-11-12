import json
import os


class Tracked(dict):
    def __init__(self, store, key, value):
        super().__init__(value)
        self.store = store
        self.key = key

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.store.save(self.key, dict(self))


class TrackedList(list):
    def __init__(self, store, key, value):
        super().__init__(value)
        self.store = store
        self.key = key

    def append(self, value):
        super().append(value)
        self.store.save(self.key, list(self))


class RedisMap:
    def __init__(self, client, prefix, hours):
        self.client = client
        self.prefix = prefix
        self.seconds = hours * 3600

    def _name(self, key):
        return self.prefix + str(key)

    def save(self, key, value):
        self.client.set(self._name(key), json.dumps(value), ex=self.seconds)

    def _wrap(self, key, value):
        if isinstance(value, dict):
            return Tracked(self, key, value)
        if isinstance(value, list):
            return TrackedList(self, key, value)
        return value

    def get(self, key, default=None):
        raw = self.client.get(self._name(key))
        if raw is None:
            return default
        return self._wrap(key, json.loads(raw))

    def __getitem__(self, key):
        value = self.get(key, None)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.save(key, value)

    def __delitem__(self, key):
        self.client.delete(self._name(key))

    def __contains__(self, key):
        return self.client.exists(self._name(key)) == 1

    def pop(self, key, default=None):
        value = self.get(key, None)
        if value is None:
            return default
        self.client.delete(self._name(key))
        return value

    def setdefault(self, key, default):
        current = self.get(key, None)
        if current is not None:
            return current
        self.save(key, default)
        return self.get(key, default)

    def items(self):
        for key in self.client.scan_iter(self.prefix + "*"):
            name = key.decode() if isinstance(key, bytes) else key
            yield name[len(self.prefix):], self.get(name[len(self.prefix):])

    def values(self):
        return [value for _, value in self.items()]


def attach():
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return
    import redis
    import server
    client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    client.ping()
    server.SESSIONS = RedisMap(client, "ekko:session:", 8)
    server.ATTEMPTS = RedisMap(client, "ekko:attempt:", 1)
    server.IP_ATTEMPTS = RedisMap(client, "ekko:ip:", 1)
