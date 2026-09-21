# Benchmark Summary & Performance Baseline

## Empirical Performance Profile

| Dataset | Samples | Features | Champion Algorithm | CV Training Time (s) | Peak RAM (MB) | P95 Latency (ms) |
|:---|:---:|:---:|:---|:---:|:---:|:---:|
| **California Housing** | 20,640 | 8 | RandomForestRegressor | 3.07s | 17.18 MB | 32.4 ms |
| **Customer Churn** | 10,000 | 12 | GradientBoostingClassifier | 1.45s | 12.30 MB | 28.1 ms |
| **Synthetic Benchmark** | 5,000 | 20 | LogisticRegression | 0.82s | 8.45 MB | 14.2 ms |

Refer to [`evidence/ml/benchmark-report.json`](file:///d:/Python/Data%20sets%20by%20campusx/Mangesh/evidence/ml/benchmark-report.json) for machine-readable benchmark outputs.
