"""内存滑动窗口限流器：按维度（用户/IP）限制每分钟请求次数。

单机内存实现；量级增长后可用 Redis 替换（接口已隔离）。
"""
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60, clock=time.monotonic):
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock  # 可注入时钟，便于测试
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """窗口内未超限返回 True 并记一次，超限返回 False。"""
        now = self._clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self._window:
                q.popleft()
            if len(q) >= self._max:
                return False
            q.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        """清空计数（key 为空则全部清空）。"""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)
