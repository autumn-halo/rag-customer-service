"""内存缓存单元测试：LRU 淘汰、TTL 过期（可注入时钟）。"""
from app.services.cache import MemoryCache, chat_cache_key


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_set_and_get():
    c = MemoryCache(max_entries=10)
    c.set("k", "v", ttl=60)
    assert c.get("k") == "v"
    assert c.get("missing") is None


def test_ttl_expiry():
    clock = FakeClock()
    c = MemoryCache(max_entries=10, clock=clock)
    c.set("k", "v", ttl=60)
    clock.advance(59)
    assert c.get("k") == "v"
    clock.advance(2)
    assert c.get("k") is None


def test_lru_eviction():
    c = MemoryCache(max_entries=2)
    c.set("a", "1", ttl=60)
    c.set("b", "2", ttl=60)
    c.get("a")  # 访问 a，让 b 成为最久未使用
    c.set("c", "3", ttl=60)
    assert c.get("b") is None
    assert c.get("a") == "1"
    assert c.get("c") == "3"


def test_clear():
    c = MemoryCache()
    c.set("k", "v", ttl=60)
    c.clear()
    assert c.get("k") is None


def test_chat_cache_key_stable_and_order_insensitive():
    k1 = chat_cache_key("qwen-plus", "退货流程", ["c2", "c1"])
    k2 = chat_cache_key("qwen-plus", "退货流程", ["c1", "c2"])
    assert k1 == k2  # 片段顺序不影响键
    assert k1 != chat_cache_key("qwen-plus", "发货时间", ["c1", "c2"])
    assert k1 != chat_cache_key("qwen-turbo", "退货流程", ["c1", "c2"])
