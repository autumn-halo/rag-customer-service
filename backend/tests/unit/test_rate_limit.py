"""滑动窗口限流器单元测试：窗口计数与恢复（可注入时钟）。"""
from app.core.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_up_to_limit_then_blocks():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60, clock=clock)
    assert limiter.allow("u1")
    assert limiter.allow("u1")
    assert limiter.allow("u1")
    assert not limiter.allow("u1")  # 第 4 次被拒


def test_keys_are_isolated():
    limiter = SlidingWindowRateLimiter(max_requests=1)
    assert limiter.allow("u1")
    assert not limiter.allow("u1")
    assert limiter.allow("u2")  # 别的用户不受影响


def test_window_slides():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60, clock=clock)
    assert limiter.allow("u1")
    assert limiter.allow("u1")
    assert not limiter.allow("u1")
    clock.advance(61)  # 窗口滑过后恢复
    assert limiter.allow("u1")


def test_reset():
    limiter = SlidingWindowRateLimiter(max_requests=1)
    assert limiter.allow("u1")
    assert not limiter.allow("u1")
    limiter.reset("u1")
    assert limiter.allow("u1")
