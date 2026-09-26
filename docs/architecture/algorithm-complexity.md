# Algorithmic Complexity Contracts & Data Structures

This document defines the formal time, space, and invariant contracts for algorithmic primitives used across the Intelligent ML Studio platform.

---

## 1. Sliding-Window Rate Limiter (`app.core.rate_limiter.SlidingWindowRateLimiter`)

* **Primary Data Structure**: `collections.defaultdict(collections.deque[float])` (Monotonic timestamp double-ended queue per client key).
* **Workload Characteristics**: High concurrency, bursty ingress traffic, time-monotonic arrivals.

### Complexity Contract
| Operation | Time Complexity | Space Complexity | Description |
| :--- | :--- | :--- | :--- |
| **Check / Record** | Amortized $\mathcal{O}(1)$ | $\mathcal{O}(R_{\text{window}})$ | Expired timestamps are popped from the left ($\mathcal{O}(1)$ per pop) until the head is within the active window, then the current timestamp is appended ($\mathcal{O}(1)$). Each timestamp is pushed once and popped once. |
| **Periodic Sweep** | $\mathcal{O}(K)$ | $\mathcal{O}(1)$ | Every 300s, stale keys whose deques are empty are purged from the hash map. |

### Invariants
1. **Monotonicity**: Elements within each deque are strictly non-decreasing: $t_0 \le t_1 \le \dots \le t_{n-1}$.
2. **Exact Windowing**: At any instant $T$, no element in queue $Q_k$ has timestamp $t \le T - W_{\text{seconds}}$.

---

## 2. LRU Model Serving Cache (`app.services.model_cache.ModelCache`)

* **Primary Data Structure**: `collections.OrderedDict` (Hash map + Doubly Linked List node pointers).
* **Workload Characteristics**: Skewed Zipfian inference traffic over trained model weights.

### Complexity Contract
| Operation | Time Complexity | Space Complexity | Description |
| :--- | :--- | :--- | :--- |
| **Lookup (`get`)** | $\mathcal{O}(1)$ expected | $\mathcal{O}(1)$ | Hash lookup + pointer update to move hit node to the end of the DLL. |
| **Insert / Evict (`put`)** | $\mathcal{O}(1)$ expected | $\mathcal{O}(1)$ | If cache exceeds capacity $C$, node at DLL head is popped in $\mathcal{O}(1)$ and freed. |

### Invariants
1. **Bounded Resident Memory**: $|Cache| \le C_{\text{max\_models}}$ at all times.
2. **Recency Ordering**: Node at position $0$ is always the least recently accessed model artifact.

---

## 3. Top-K Feature Selection Ranker (`app.services.selectors.TopKRanker`)

* **Primary Data Structure**: Bounded Min-Heap (`heapq`) / Timsort with composite 3-tier lexicographical comparator.
* **Workload Characteristics**: High-dimensional feature selection ($p \in [10, 10^6]$ candidate columns, selecting $k \ll p$).

### Complexity Contract
| Regime | Algorithm | Time Complexity | Working Space | Condition |
| :--- | :--- | :--- | :--- | :--- |
| **Small Subset Selection** | Bounded Min-Heap (`heapq.nsmallest`) | $\mathcal{O}(p \log k)$ | $\mathcal{O}(k)$ | $p > 2k$ |
| **Full / Large Selection** | Deterministic Timsort | $\mathcal{O}(p \log p)$ | $\mathcal{O}(p)$ | $p \le 2k$ |

### Tie-Breaking Comparator Contract (SRS §2.7)
For two features $A = (name_A, score_A, rank\_sum_A)$ and $B = (name_B, score_B, rank\_sum_B)$:
$$A \succ B \iff \begin{cases} 
score_A > score_B & \text{(Primary: higher score)} \\ 
score_A = score_B \land rank\_sum_A < rank\_sum_B & \text{(Secondary: lower aggregate rank sum)} \\ 
score_A = score_B \land rank\_sum_A = rank\_sum_B \land name_A < name_B & \text{(Tertiary: lexicographical ascending)} 
\end{cases}$$

---

## 4. Keyset / Cursor Pagination (`app.repositories.base_keyset`)

* **Primary Mechanism**: B-Tree composite index seek `(created_at DESC, id DESC)`.
* **Workload Characteristics**: Deep pagination over unbounded append-only logs (`audit_logs`, `predictions`, `experiments`).

### Complexity Contract vs Offset Pagination
| Metric | Offset Pagination (`OFFSET S LIMIT L`) | Keyset Pagination (`WHERE (created_at, id) < cursor LIMIT L`) |
| :--- | :--- | :--- |
| **Query Time (Page 1)** | $\mathcal{O}(L)$ | $\mathcal{O}(L)$ |
| **Query Time (Deep Page $S$)** | $\mathcal{O}(S + L)$ (Full index/table scan & discard) | $\mathcal{O}(\log N + L)$ (Direct B-Tree pointer seek) |
| **Consistency under Concurrency** | Prone to page drift and duplicate reads on insertions | Deterministic snapshot pagination without missed/duplicate rows |

---

## 5. Streaming Idempotency & Artifact Checksumming

* **Primary Primitives**: SHA-256 block-streaming hasher.
* **Workload Characteristics**: Multi-gigabyte dataset and model weight serialization.

### Complexity Contract
* **Time**: $\mathcal{O}(B)$ where $B$ is the byte length of the serialized payload.
* **Space**: $\mathcal{O}(1)$ working memory via 64KB chunked buffer streaming (zero full-file RAM buffering).
