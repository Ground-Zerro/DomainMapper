import heapq
from collections import Counter
from collections.abc import Collection, Iterable
from ipaddress import IPv4Network

from .console import ask, green, yellow

FULL_MASK = 0xFFFFFFFF
HOST_PREFIX = 32
WIDEST_PREFIX = 16
EXACT = "exact"
MASKS = tuple(FULL_MASK ^ (FULL_MASK >> prefix) for prefix in range(HOST_PREFIX + 1))

Block = tuple[int, int]


def block_size(prefix: int) -> int:
    return 1 << (HOST_PREFIX - prefix)


def collapse(blocks: Iterable[Block]) -> list[Block]:
    merged: list[Block] = []
    for block in sorted(blocks):
        merged.append(block)
        while len(merged) > 1:
            (left, prefix), (right, right_prefix) = merged[-2], merged[-1]
            size = block_size(prefix)
            if prefix != right_prefix or left & size or right != left | size:
                break
            merged[-2:] = [(left, prefix - 1)]
    return merged


class SupernetTree:
    def __init__(self, blocks: list[Block]):
        self._blocks = blocks
        self._covered: Counter[Block] = Counter()
        self._routes: Counter[Block] = Counter()
        self._merged: set[Block] = set()
        for network, prefix in blocks:
            size = block_size(prefix)
            for parent in range(WIDEST_PREFIX, prefix):
                supernet = (network & MASKS[parent], parent)
                self._covered[supernet] += size
                self._routes[supernet] += 1
        self._queue = [self._entry(supernet) for supernet, routes in self._routes.items() if routes > 1]
        heapq.heapify(self._queue)

    def shrink(self, limit: int) -> list[Block]:
        total = len(self._blocks)
        while total > limit and self._queue:
            cost, _, supernet = heapq.heappop(self._queue)
            if self._routes[supernet] > 1 and cost == self._cost(supernet) and not self._absorbed(supernet):
                total -= self._merge(supernet)
        return collapse(block for block in (*self._merged, *self._blocks) if not self._absorbed(block))

    def _cost(self, supernet: Block) -> float:
        return (block_size(supernet[1]) - self._covered[supernet]) / (self._routes[supernet] - 1)

    def _entry(self, supernet: Block) -> tuple[float, int, Block]:
        return self._cost(supernet), -supernet[1], supernet

    def _absorbed(self, block: Block) -> bool:
        network, prefix = block
        return any((network & MASKS[parent], parent) in self._merged for parent in range(WIDEST_PREFIX, prefix))

    def _merge(self, supernet: Block) -> int:
        network, prefix = supernet
        saved = self._routes[supernet] - 1
        added = block_size(prefix) - self._covered[supernet]
        self._routes[supernet] = 1
        self._covered[supernet] = block_size(prefix)
        self._merged.add(supernet)
        for parent in range(WIDEST_PREFIX, prefix):
            ancestor = (network & MASKS[parent], parent)
            self._routes[ancestor] -= saved
            self._covered[ancestor] += added
            if self._routes[ancestor] > 1:
                heapq.heappush(self._queue, self._entry(ancestor))
        return saved


class Aggregation:
    title = "без потерь (склейка соседних адресов)"

    def apply(self, addresses: Collection[int]) -> list[IPv4Network]:
        return [IPv4Network(block) for block in self._blocks(addresses)]

    def _blocks(self, addresses: Collection[int]) -> list[Block]:
        return collapse((address, HOST_PREFIX) for address in addresses)


class LimitedAggregation(Aggregation):
    def __init__(self, limit: int):
        self.limit = limit
        self.title = f"не более {limit} маршрутов"

    def _blocks(self, addresses: Collection[int]) -> list[Block]:
        blocks = super()._blocks(addresses)
        if len(blocks) <= self.limit:
            return blocks
        blocks = SupernetTree(blocks).shrink(self.limit)
        if len(blocks) > self.limit:
            print(yellow(f"Лимит {self.limit} недостижим без подсетей шире /{WIDEST_PREFIX}, минимально возможное число маршрутов: {len(blocks)}."))
        return blocks


def parse_aggregation(value: str) -> Aggregation | None:
    value = value.strip().lower()
    if value == EXACT:
        return Aggregation()
    if value.isdigit() and int(value) > 0:
        return LimitedAggregation(int(value))
    return None


def choose_aggregation(configured: Aggregation | None) -> Aggregation:
    if configured is not None:
        return configured
    answer = ask(f"\n{yellow('Ограничить число маршрутов?')}\nВведите максимальное количество или {green('Enter')} - без ограничения: ")
    return parse_aggregation(answer) or Aggregation()
