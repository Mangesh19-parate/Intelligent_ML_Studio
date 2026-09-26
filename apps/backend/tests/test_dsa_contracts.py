import time
import pytest
from fastapi import HTTPException
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.services.selectors import TopKRanker, sort_features_with_tie_break, apply_top_k_percent_selection
from app.infrastructure.storage.model_cache import BoundedModelCache


class TestSlidingWindowRateLimiterDSA:
    def test_deque_rate_limiting_sliding_window(self):
        limiter = SlidingWindowRateLimiter()
        key = "client-127.0.0.1"

        # Allow 3 requests per 2 seconds
        for _ in range(3):
            limiter.check_rate_limit(key=key, max_requests=3, window_seconds=2)

        # 4th request within window must raise 429
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(key=key, max_requests=3, window_seconds=2)
        assert exc_info.value.status_code == 429

        # Simulate time passage
        time.sleep(2.1)
        # Should now succeed as expired timestamps are popped from deque
        limiter.check_rate_limit(key=key, max_requests=3, window_seconds=2)
        assert len(limiter._requests[key]) == 1


class TestTopKRankerDSA:
    def test_top_k_heap_vs_sort_equivalence(self):
        """Tests that O(p log k) min-heap and O(p log p) full sort yield identical results."""
        # 100 features, selecting top 10 (p > 2k triggers heap path)
        features = [f"feat_{i:03d}" for i in range(100)]
        scores = {f"feat_{i:03d}": (i % 20) * 0.05 for i in range(100)}
        rank_sums = {f"feat_{i:03d}": float(100 - i) for i in range(100)}

        items = [(features[i], scores[features[i]], rank_sums[features[i]]) for i in range(100)]

        heap_res = TopKRanker.select_top_k(items, k=10)
        sort_res = sorted(items, key=TopKRanker._rank_key)[:10]

        assert heap_res == sort_res
        assert len(heap_res) == 10

    def test_top_k_tie_breaking_3_tiers(self):
        """Tests exact 3-tier tie-breaking: score desc -> rank_sum asc -> name asc."""
        items = [
            ("gamma", 0.85, 12.0),
            ("alpha", 0.85, 10.0),   # Same score, lower rank sum -> should beat gamma
            ("beta", 0.85, 10.0),    # Same score, same rank sum, alpha < beta -> alpha beats beta
            ("zeta", 0.90, 50.0),    # Higher score -> beats all
        ]

        ranked = TopKRanker.select_top_k(items, k=4)
        names = [item[0] for item in ranked]
        assert names == ["zeta", "alpha", "beta", "gamma"]


class TestLRUModelCacheDSA:
    def test_lru_eviction_policy(self):
        cache = BoundedModelCache(max_entries=2, ttl_seconds=300.0)
        cache.put("model_A", {"weights": 1})
        cache.put("model_B", {"weights": 2})

        # Touch model_A to make model_B the least recently used
        assert cache.get("model_A") is not None

        # Insert model_C -> model_B should be evicted
        cache.put("model_C", {"weights": 3})

        assert cache.get("model_B") is None
        assert cache.get("model_A") is not None
        assert cache.get("model_C") is not None
