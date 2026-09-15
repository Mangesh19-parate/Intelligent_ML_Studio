# Complete Software Testing Workflow Guide

## Purpose
A rigorous, end-to-end testing workflow ensures that the ML Studio application is resilient, secure, bug-free, and handles real-world chaotic conditions with mathematical guarantees.

---

## 1. Understand the Application
Before testing, fully understand the app’s features, user flow, and expected behavior.
- **Read requirements or PRD**: Tabular ML lifecycle (Ingestion, Split, Train, Evaluate, Explain, Govern, Deploy).
- **Identify critical flows**: Authentication (JWT + 2FA TOTP), Dataset upload & hash seal, Model training & leaderboard evaluation, Dual-key governance approvals, Real-time REST prediction.
- **Know expected outputs for each action**: Status transitions (DRAFT → SEALED → TRAINED → APPROVED → DEPLOYED), error boundaries, and deterministic audit trails.

---

## 2. Define Test Scenarios
Break the app into distinct user scenarios:
- **Authentication & Security Flow**: User registration, login, 2FA challenge, recovery key fallback, rate limiting.
- **Data Ingestion & Integrity**: CSV upload, schema inference, target validation, immutable partition sealing.
- **Model Training & Experimentation**: Baseline models, cross-validation, hyperparameter evaluation, metric leaderboards.
- **Governance & Approvals**: Tier-based policy evaluation, dual-signoff gates, model passport generation.
- **Real-Time Deployment & Inference**: REST endpoint provisioning, low-latency prediction, drift monitoring.

---

## 3. Perform Manual Testing
Start with manual testing:
- **Happy Path**: Complete standard golden workflows without interruptions.
- **Edge Cases**: Empty inputs, out-of-range floats, invalid dates, malformed JSON bodies.
- **Random/Spam Actions**: Double-clicking submit buttons, rapid route hopping, canceling operations mid-flight.
- **Goal**: Break the system like a real user before deploying.

---

## 4. Edge Case Testing
Test unusual conditions:
- **Very Large Inputs**: Datasets with 100k+ rows, 100+ columns, oversized payload requests.
- **Special Characters**: Unicode strings (`ñ`, `ø`, `漢字`), SQL injection payloads (`' OR 1=1 --`), XSS tags (`<script>alert(1)</script>`), control characters.
- **Rapid Clicks**: Button debouncing, concurrent asynchronous API dispatches.

---

## 5. Browser & Device Testing
Use Chrome DevTools:
- **Simulate Slow Network**: Slow 3G / Fast 3G throttling to verify skeleton loaders and loading spinners.
- **Test Offline Mode**: Network disconnect during navigation or inference requests to verify error boundaries.
- **Different Screen Sizes**: Mobile (375px), Tablet (768px), Laptop (1024px), Desktop (1440px+).

---

## 6. API Testing
Test backend independently:
- **Use Postman / curl / HTTP scripts**: Test endpoints without frontend safeguards.
- **Modify Request Data**: Negative numbers, mismatched data types, missing required fields.
- **Unauthorized Actions**: Non-admin accessing admin routes, regular user attempting governance signoffs.
- **Goal**: Ensure backend validates everything at the boundary.

---

## 7. Automation Testing
Use automated frameworks:
- **Vitest & React Testing Library**: Unit and component interaction tests for React frontend.
- **Pytest**: Unit, service, route, and end-to-end pipeline tests for FastAPI backend.
- **Browser Automation / Subagent**: Automated end-to-end visual and functional flow validation.
- **Run tests on every deploy/PR**.

---

## 8. Regression Testing
After every codebase change:
- **Re-test Old Features**: Re-run complete test suites (477+ backend tests, 40+ frontend tests).
- **Ensure Nothing Broke**: Automatic prevention of regression bugs before merging to `main`.

---

## 9. Performance & Load Testing
Check app under sustained pressure:
- **Concurrent Users**: Simultaneous predictions against deployed models.
- **Latency SLAs**: P95 < 50ms, P99 < 100ms inference verification.
- **Benchmark Scripts**: Automated resource consumption checks.

---

## 10. Error Monitoring & Logging
Check console, logs, and audit trails:
- **Fix Warnings**: Address React key warnings, deprecated API calls, and lint errors.
- **Track Errors**: Structured logging with request IDs, stack traces, and actionable error messages.

---

## 11. User Simulation
Act like a real user:
- **Random Clicks & Fast Navigation**: Unordered tab switching during dataset upload or model training.
- **Unexpected Behavior**: Back/forward browser buttons, refreshing mid-training.

---

## 12. Final Rule
> *"If you didn't try to break your app, you didn't test it."*
