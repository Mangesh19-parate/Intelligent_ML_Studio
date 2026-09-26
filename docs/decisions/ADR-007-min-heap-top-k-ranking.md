# ADR-007: Min-Heap Top-K Feature Selection Ranker

## Status
Accepted

## Context
In high-dimensional feature selection ($p \gg 1,000$ candidate features, selecting $k = 50$), full sort algorithms execute in $\mathcal{O}(p \log p)$ time and require $\mathcal{O}(p)$ working memory.

## Decision
We introduced `TopKRanker` in `app.services.selectors` using `heapq.nsmallest` with a composite 3-tier tie-breaking comparator `(-score, rank_sum, name)`:
- When $p > 2k$: Uses a bounded min-heap operating in $\mathcal{O}(p \log k)$ time and $\mathcal{O}(k)$ working space.
- When $p \le 2k$: Uses standard Timsort operating in $\mathcal{O}(p \log p)$ time.

## Invariants
1. Primary: Higher ensemble score descending (`-score`).
2. Secondary: Lower aggregate rank sum ascending (`+rank_sum`).
3. Tertiary: Lexicographical column name ascending (`+name`).

## Consequences
- Significant performance gain when selecting sparse feature subsets from ultra-high-dimensional datasets.
- 100% deterministic ranking across repeated executions and platforms.
