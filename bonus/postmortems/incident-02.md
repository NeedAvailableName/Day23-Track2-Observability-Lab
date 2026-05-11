# Incident-02: Traffic Spike with Backend Degradation

**Date:** 2026-05-11
**Duration:** ~73 seconds
**Severity:** High
**Detection time:** 20 seconds

---

## Timeline

| Time | Event |
|------|-------|
| T+0s | Chaos injection: 20 concurrent requests per wave, 50% with `fail=true` |
| T+2s | First wave completes: 10/20 requests return 503 errors |
| T+7s | Second wave: error pattern continues |
| T+11s | Third wave: Prometheus error rate climbing |
| T+20s | Error rate reaches 0.77/s — **DETECTED** (threshold: 0.1/s) |
| T+20s | Injection stops, monitoring continues |
| T+73s | Error rate returns to 0 — natural recovery |

## Detection

- **Signal:** `rate(inference_requests_total{status='error'}[1m])` exceeded 0.1/s
- **Time to detect:** 20 seconds (3 waves needed to accumulate enough data points)
- **Alert rule:** `SLO_InferenceSuccessRate_BurnRate` — fires on error rate burn

## Mitigation

- Injection self-terminated after 5 waves (100 total requests)
- No manual intervention needed — the mock model recovered once bad traffic stopped
- In production, mitigation would be: circuit breaker, rate limiting, or traffic shifting

## Root Cause

Simulated backend degradation: 50% of requests were sent with `fail=true`, causing the model to return 503 Service Unavailable. This mimics a scenario where the model serving infrastructure is partially degraded (GPU OOM, model loading timeout, upstream API failure).

## Action Items

1. ✅ **Implemented:** Error rate alerting via multi-window burn-rate rules in `slo-burn-rate.yml`
2. 📋 **TODO:** Add circuit breaker pattern to the inference client — stop sending traffic after N consecutive failures
3. 📋 **TODO:** Implement request queuing with backpressure — prevent thundering herd during recovery
4. 📋 **TODO:** Add per-model error rate labels for granular alerting

## Lessons Learned

- 20-second detection is reasonable for a burst scenario — faster than most manual monitoring
- The burn-rate approach correctly distinguishes a sustained error spike from a transient blip
- Without `fail=true` support, this chaos test would be hard to reproduce — the `fail` parameter is valuable for testing
- The error rate naturally decayed after injection stopped — good sign that the system is self-healing
