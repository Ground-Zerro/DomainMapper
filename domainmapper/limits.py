import asyncio
import time

CONTROL_WINDOW = 2.0
CONGESTION_THRESHOLD = 0.05
CONGESTION_MIN_EVENTS = 3
RECOVERY_THRESHOLD = 0.01
DECREASE_FACTOR = 0.6
INCREASE_SHARE = 0.1
MIN_RATE = 2.0
MAX_IN_FLIGHT = 256


class RateLimiter:
    def __init__(self, rate: float):
        self._interval = 1.0 / rate
        self._next_slot = 0.0

    @property
    def rate(self) -> float:
        return 1.0 / self._interval

    async def wait(self) -> None:
        now = time.monotonic()
        slot = max(now, self._next_slot)
        self._next_slot = slot + self._interval
        if slot > now:
            await asyncio.sleep(slot - now)


class AdaptiveRateLimiter(RateLimiter):
    def __init__(self, ceiling: float):
        super().__init__(ceiling)
        self._ceiling = ceiling
        self._window_started = time.monotonic()
        self._completed = 0
        self._congested = 0

    def feedback(self, congested: bool) -> None:
        self._completed += 1
        self._congested += congested
        now = time.monotonic()
        if now - self._window_started < CONTROL_WINDOW:
            return
        share = self._congested / self._completed
        if self._congested >= CONGESTION_MIN_EVENTS and share > CONGESTION_THRESHOLD:
            self._set_rate(max(MIN_RATE, self.rate * DECREASE_FACTOR))
        elif share <= RECOVERY_THRESHOLD:
            self._set_rate(min(self._ceiling, self.rate + self._ceiling * INCREASE_SHARE))
        self._window_started = now
        self._completed = 0
        self._congested = 0

    def _set_rate(self, rate: float) -> None:
        self._interval = 1.0 / rate


class QueryBudget:
    def __init__(self, total_rate: float):
        self.limiter = RateLimiter(total_rate)
        self.slots = asyncio.Semaphore(MAX_IN_FLIGHT)
