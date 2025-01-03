from rick_db import QueryCache


class TestQueryCache:

    def test_cache(self):
        cache = QueryCache()
        for i in range(100):
            key = "key_" + str(i)
            value = "value_" + str(i)
            assert cache.get(key) is None
            assert cache.has(key) is False
            cache.set(key, value)
            assert cache.get(key) == value
            assert cache[key] == value
            assert cache.has(key) is True

        assert len(cache) == 100
        cache.remove("key_10")
        assert cache.has("key_10") is False
        assert len(cache) == 99

        replica = cache.copy()
        assert len(replica) == 99
        replica.remove("key_9")
        assert len(replica) == 98
        assert len(cache) == 99
        assert cache.has("key_9") is True  # delete was on replica

        replica.purge()
        assert len(replica) == 0
        assert len(cache) == 99
