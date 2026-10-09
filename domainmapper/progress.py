import asyncio
import shutil
import sys
import time
from collections import deque
from enum import IntEnum

REFRESH_INTERVAL = 0.25
PLAIN_REFRESH_INTERVAL = 5.0
SPEED_WINDOW = 3.0
WARMUP = 1.0
MIN_BAR_WIDTH = 10
MAX_BAR_WIDTH = 40
BAR_FILLED = "█"
BAR_EMPTY = "░"
UNKNOWN_TIME = "--:--"


def format_duration(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class Outcome(IntEnum):
    RESOLVED = 0
    MISSING = 1
    TIMEOUT = 2
    UNAVAILABLE = 3
    INVALID = 4


RETRYABLE = frozenset({Outcome.TIMEOUT, Outcome.UNAVAILABLE})
FAILURES = (Outcome.TIMEOUT, Outcome.UNAVAILABLE, Outcome.INVALID)


class ServerProgress:
    __slots__ = ("total", "counts")

    def __init__(self, total: int):
        self.total = total
        self.counts = [0] * len(Outcome)

    @property
    def processed(self) -> int:
        return sum(self.counts)

    def record(self, outcome: Outcome) -> None:
        self.counts[outcome] += 1


class ResolveProgress:
    def __init__(self, servers: int, domains: int, expected_rate: float):
        self.servers = [ServerProgress(domains) for _ in range(servers)]
        self.total = servers * domains
        self._expected_rate = expected_rate
        self._interactive = sys.stdout.isatty()
        self._digits = len(str(self.total))
        self._samples: deque[tuple[float, int]] = deque()
        self._started = 0.0
        self._task: asyncio.Task[None] | None = None

    @property
    def processed(self) -> int:
        return sum(server.processed for server in self.servers)

    def count(self, outcome: Outcome) -> int:
        return sum(server.counts[outcome] for server in self.servers)

    @property
    def failed(self) -> int:
        return sum(self.count(outcome) for outcome in FAILURES)

    async def __aenter__(self) -> "ResolveProgress":
        self._started = time.monotonic()
        self._samples.append((self._started, 0))
        self._task = asyncio.create_task(self._refresh())
        return self

    async def __aexit__(self, *_: object) -> None:
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._draw()
        if self._interactive:
            sys.stdout.write("\n")
        sys.stdout.flush()

    async def _refresh(self) -> None:
        interval = REFRESH_INTERVAL if self._interactive else PLAIN_REFRESH_INTERVAL
        while True:
            await asyncio.sleep(interval)
            self._draw()

    def _draw(self) -> None:
        now = time.monotonic()
        processed = self.processed
        self._samples.append((now, processed))
        while len(self._samples) > 2 and now - self._samples[1][0] >= SPEED_WINDOW:
            self._samples.popleft()
        width = shutil.get_terminal_size().columns - 1 if self._interactive else sys.maxsize
        line = self._line(now, processed, width)
        sys.stdout.write(f"\r{line.ljust(width)}" if self._interactive else f"{line}\n")
        sys.stdout.flush()

    def _speed(self, now: float, processed: int) -> float:
        start, count = self._samples[0]
        return (processed - count) / (now - start) if now > start else 0.0

    def _remaining(self, elapsed: float) -> str:
        worst = 0.0
        for server in self.servers:
            processed = server.processed
            left = server.total - processed
            if not left:
                continue
            rate = self._expected_rate if elapsed < WARMUP else processed / elapsed
            if not rate:
                return UNKNOWN_TIME
            worst = max(worst, left / rate)
        return format_duration(worst)

    def _line(self, now: float, processed: int, width: int) -> str:
        elapsed = now - self._started
        ratio = processed / self.total if self.total else 1.0
        head = f" {ratio:6.1%} | {processed:>{self._digits}}/{self.total}"
        tail = f" | осталось ~{self._remaining(elapsed)}"
        stats = (
            f"{head} | сбоев: {self.failed:>{self._digits}} | {self._speed(now, processed):5.0f} запр/с"
            f" | прошло {format_duration(elapsed)}{tail}"
        )
        if len(stats) + MIN_BAR_WIDTH + 2 > width:
            stats = f"{head}{tail}"
        bar_width = max(MIN_BAR_WIDTH, min(MAX_BAR_WIDTH, width - len(stats) - 2))
        filled = round(bar_width * ratio)
        return f"[{BAR_FILLED * filled}{BAR_EMPTY * (bar_width - filled)}]{stats}"[:width]
