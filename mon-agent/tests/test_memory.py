import pytest
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.memory import ProfileCache

class TestProfileCache:
    def test_cache_hit(self):
        cache = ProfileCache(ttl=60)
        calls = []
        def loader(uid):
            calls.append(uid)
            return {"nom": uid}
        p1 = cache.get("user1", loader)
        assert len(calls) == 1
        p2 = cache.get("user1", loader)
        assert len(calls) == 1
        assert p1 == p2

    def test_cache_miss(self):
        cache = ProfileCache(ttl=60)
        calls = []
        def loader(uid):
            calls.append(uid)
            return {"nom": uid}
        cache.get("user1", loader)
        cache.get("user2", loader)
        assert len(calls) == 2

    def test_cache_invalidation(self):
        cache = ProfileCache(ttl=60)
        calls = []
        def loader(uid):
            calls.append(uid)
            return {"nom": uid}
        cache.get("user1", loader)
        cache.invalidate("user1")
        cache.get("user1", loader)
        assert len(calls) == 2

    def test_cache_ttl_expires(self):
        cache = ProfileCache(ttl=0)
        calls = []
        def loader(uid):
            calls.append(uid)
            return {"nom": uid}
        cache.get("user1", loader)
        cache.get("user1", loader)
        assert len(calls) == 2
