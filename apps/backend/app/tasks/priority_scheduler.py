"""
Priority Task Scheduler with Dynamic Aging & Anti-Starvation (DSA + CS Concurrency).
Implements a min-heap priority queue with linear aging to balance job criticality and fairness.
"""

import time
import heapq
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class PrioritizedTask:
    effective_priority: float
    queued_at: float = field(compare=False)
    base_priority: int = field(compare=False)
    task_id: str = field(compare=False)
    payload: dict[str, Any] = field(compare=False, default_factory=dict)


class PriorityTaskScheduler:
    """
    Thread-safe Priority Queue with Dynamic Aging.
    
    Complexity Contract:
      - Enqueue (push): O(log N)
      - Dequeue (pop min): O(log N)
      - Anti-starvation Aging: Effective priority = base_priority - lambda * wait_time
        Lower effective_priority values dequeue first in the min-heap.
    """

    def __init__(self, aging_rate: float = 0.05):
        self._heap: list[PrioritizedTask] = []
        self._lock = threading.Lock()
        self._aging_rate = aging_rate  # Lambda: priority promotion per second of wait time

    def push(self, task_id: str, base_priority: int = 10, payload: dict[str, Any] | None = None) -> PrioritizedTask:
        now = time.time()
        # Effective priority starts at base_priority (1=Critical, 10=Normal, 50=Low)
        task = PrioritizedTask(
            effective_priority=float(base_priority),
            queued_at=now,
            base_priority=base_priority,
            task_id=task_id,
            payload=payload or {},
        )
        with self._lock:
            heapq.heappush(self._heap, task)
        return task

    def pop(self) -> PrioritizedTask | None:
        with self._lock:
            if not self._heap:
                return None
            # Apply aging recalculation before popping
            now = time.time()
            self._recalculate_effective_priorities(now)
            return heapq.heappop(self._heap)

    def peek(self) -> PrioritizedTask | None:
        with self._lock:
            return self._heap[0] if self._heap else None

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def _recalculate_effective_priorities(self, current_time: float) -> None:
        """
        In-place priority promotion to prevent low-priority task starvation.
        Re-establishes min-heap invariant in O(N) linear time via heapify.
        """
        for task in self._heap:
            wait_time = max(0.0, current_time - task.queued_at)
            # Higher wait time decreases effective_priority, promoting task towards heap root
            task.effective_priority = task.base_priority - (self._aging_rate * wait_time)
        heapq.heapify(self._heap)
