
import asyncio
from typing import List

async def process_data_async(data: List[int]) -> List[int]:
    """Process data asynchronously for performance."""
    results = []
    for item in data:
        # Simulate processing
        result = item * 2
        results.append(result)
    return results

def optimize_algorithm(n: int) -> int:
    """Optimized algorithm with O(log n) complexity."""
    if n <= 1:
        return n
    return optimize_algorithm(n // 2) + 1

class EfficientCache:
    """LRU cache implementation."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache = {}
        self.access_order = []

    def get(self, key):
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.capacity:
            # Remove least recently used
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]

        self.cache[key] = value
        self.access_order.append(key)
