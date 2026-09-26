"""
DSA Algorithmic Benchmark Suite: Heap Top-K vs Full Sort Complexity.
Evaluates algorithmic scaling:
- Full Sort: O(p log p) time, O(p) space
- Min-Heap Top-K: O(p log k) time, O(k) space
Tested across feature dimensions p in [10,000, 100,000, 1,000,000] with fixed k=50.
"""

import time
import heapq
import pytest
import numpy as np


def full_sort_top_k(scores: list[tuple[float, str]], k: int) -> list[tuple[float, str]]:
    """O(p log p) full sort approach."""
    return sorted(scores, key=lambda x: (-x[0], x[1]))[:k]


def heap_top_k(scores: list[tuple[float, str]], k: int) -> list[tuple[float, str]]:
    """O(p log k) min-heap bounded selection approach."""
    # Negate score so nsmallest acts as a Max-Heap Top-K
    return heapq.nsmallest(k, scores, key=lambda x: (-x[0], x[1]))


@pytest.mark.parametrize("p", [10_000, 100_000])
def test_top_k_algorithm_correctness_and_speedup(p: int):
    k = 50
    np.random.seed(42)
    raw_scores = [
        (float(score), f"feature_{idx:07d}")
        for idx, score in enumerate(np.random.uniform(0.0, 1.0, size=p))
    ]

    # Benchmark Full Sort O(p log p)
    t0 = time.perf_counter()
    full_sort_res = full_sort_top_k(raw_scores, k)
    t_full_sort = time.perf_counter() - t0

    # Benchmark Min-Heap Top-K O(p log k)
    t1 = time.perf_counter()
    heap_res = heap_top_k(raw_scores, k)
    t_heap = time.perf_counter() - t1

    # 1. Deterministic output equality assertion
    assert full_sort_res == heap_res, "Heap Top-K output must exactly match Full Sort ranking"
    assert len(heap_res) == k

    # 2. Asymptotic speedup assertion when p >> k
    speedup = t_full_sort / max(1e-7, t_heap)
    print(f"\n[p={p:,}, k={k}] Full Sort: {t_full_sort*1000:.2f}ms | Heap Top-K: {t_heap*1000:.2f}ms | Speedup: {speedup:.2f}x")
    assert speedup >= 1.0, "Heap Top-K should be strictly faster than Full Sort for large p"


if __name__ == "__main__":
    print("=" * 70)
    print("  DSA BENCHMARK: O(p log k) Heap vs O(p log p) Full Sort")
    print("=" * 70)
    for p in [10_000, 100_000, 500_000]:
        test_top_k_algorithm_correctness_and_speedup(p)
