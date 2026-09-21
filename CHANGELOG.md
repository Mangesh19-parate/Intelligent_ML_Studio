# Changelog

All notable changes to **Intelligent ML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-21

### Added
- **Modular Monolith + Dedicated Worker Architecture**: Clean bounded-context structure (`domain`, `application`, `ml`, `infrastructure`, `workers`).
- **Zero-Leakage ML Pipeline**: Row-hash verified immutable 80/20 train/holdout splits and fold-isolated feature selection.
- **Canonical 6-Algorithm Tournament**: Standardized multi-algorithm CV training for regression and classification tasks.
- **Cryptographic Model Passports**: Manifest generation with dataset SHA-256 hashes and HMAC-signed serialized artifacts.
- **Four-Eyes Deployment Governance**: Separation-of-duties promotion checks (`approved_by != created_by`) and one-click rollback.
- **Automated Evidence Pack**: Machine-readable JSON validation reports in `./evidence/` covering leakage invariants, benchmarks, and threat models.
- **Adversarial Leakage & SHAP Invariant Suites**: Automated test proofs enforcing zero contamination and exact mathematical additivity ($\sum \phi_i = f(x) - E[f(x)]$).
- **Multi-Tier Verification Harness**: 541 passing automated tests across backend and frontend suites.
