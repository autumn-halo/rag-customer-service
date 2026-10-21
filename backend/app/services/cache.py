"""答案缓存：相同问题秒回，省 API 费用也更快。

CacheBackend 抽象接口预留 Redis 实现（同一接口无缝替换），
当前用内存 LRU + TTL，符合"单机可跑"的轻量姿态。
"""
import hashlib
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from threading import Lock

from app.config import settings


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...

    @abstractmethod
    def set(self, key: str, value: str, ttl: int) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...


class MemoryCache(CacheBackend):
    """LRU 淘汰 + TTL 过期的内存缓存（线程安全）。"""

    def __init__(self, max_entries: int | None = None, clock=time.monotonic):
        self._max = max_entries or settings.cache_max_entries
        self._clock = clock  # 可注入时钟，便于测试
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires, value = item
            if self._clock() < expires:
                self._store.move_to_end(key)
                return value
            del self._store[key]
            return None

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._store[key] = (self._clock() + ttl, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)  # 淘汰最久未使用的

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# RedisCacheBackend：预留。实现同一接口即可无缝切换（不引 Redis 服务）。
_cache: CacheBackend = MemoryCache()


def get_cache() -> CacheBackend:
    return _cache


def chat_cache_key(model: str, question: str, chroma_ids: list[str]) -> str:
    """缓存键 = 模型 + 问题 + 命中的片段集合（知识库变了缓存自动失效）。"""
    raw = f"{model}|{question}|{','.join(sorted(chroma_ids))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
