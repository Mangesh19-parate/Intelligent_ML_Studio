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


@pytest.mark.parametrize("p", [10_000, 100_000, 1_000_000])
def test_top_k_algorithm_correctness_and_speedup(p: int):
    k = 50
    np.random.seed(42)
    raw_scores = [
        (float(score), f"feature_{idx:07d}")
        for idx, score in enumerate(np.random.uniform(0.0, 1.0, size=p))
    ]

    # 1. Warm-up phase to avoid JIT/cache cold start bias
    _ = full_sort_top_k(raw_scores[:1000], min(10, k))
    _ = heap_top_k(raw_scores[:1000], min(10, k))

    # 2. Multi-run statistical measurement (n=15 iterations for robust distribution)
    n_iterations = 10 if p >= 1_000_000 else 15
    sort_durations = []
    heap_durations = []

    full_sort_res = None
    heap_res = None

    for _ in range(n_iterations):
        # Measure Full Sort
        t0 = time.perf_counter()
        full_sort_res = full_sort_top_k(raw_scores, k)
        sort_durations.append(time.perf_counter() - t0)

        # Measure Heap Top-K
        t1 = time.perf_counter()
        heap_res = heap_top_k(raw_scores, k)
        heap_durations.append(time.perf_counter() - t1)

    # 3. Deterministic output equality assertion
    assert full_sort_res == heap_res, "Heap Top-K output must exactly match Full Sort ranking"
    assert len(heap_res) == k

    # 4. Statistical Distribution Calculation (Median & P95)
    sort_median = float(np.median(sort_durations))
    sort_p95 = float(np.percentile(sort_durations, 95))
    heap_median = float(np.median(heap_durations))
    heap_p95 = float(np.percentile(heap_durations, 95))

    speedup_median = sort_median / max(1e-7, heap_median)
    print(
        f"\n[p={p:,}, k={k}, n={n_iterations}] "
        f"Sort (Median: {sort_median*1000:.2f}ms, P95: {sort_p95*1000:.2f}ms) | "
        f"Heap (Median: {heap_median*1000:.2f}ms, P95: {heap_p95*1000:.2f}ms) | "
        f"Speedup: {speedup_median:.2f}x"
    )

    # 5. Robust scaling assertion on median runtime
    # For large dimensions (p >= 100k, k=50), O(p log k) must maintain throughput advantage
    assert heap_median > 0.0
    assert sort_median > 0.0
    if p >= 100_000:
        assert speedup_median >= 0.9, f"Heap median throughput should scale competitively with full sort at p={p}"


if __name__ == "__main__":
    print("=" * 70)
    print("  DSA BENCHMARK: O(p log k) Heap vs O(p log p) Full Sort")
    print("=" * 70)
    for p in [10_000, 100_000, 1_000_000]:
        test_top_k_algorithm_correctness_and_speedup(p)

