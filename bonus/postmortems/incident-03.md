# Incident-03: Data Poisoning — Garbage Prompts + Forced Failures

**Date:** 2026-05-11
**Duration:** ~70 seconds
**Severity:** High
**Detection time:** 20 seconds

---

## Timeline

| Time | Event |
|------|-------|
| T+0s | Chaos injection: 10 poison requests per wave (garbage prompts + `fail=true`) |
| T+7s | Wave 1: 5/10 errors, quality scores normal for non-failing requests |
| T+13s | Wave 2: 5/10 errors, error rate climbing |
| T+20s | Wave 3: error rate hits 0.36/s — **DETECTED** (threshold: 0.05/s) |
| T+20s | Injection stops |
| T+70s | Error rate returns to 0 |

## Detection

- **Signal:** `rate(inference_requests_total{status='error'}[1m])` exceeded 0.05/s
- **Time to detect:** 20 seconds
- **Alert rule:** `AI_QualityScore_Drop` and `SLO_InferenceSuccessRate_BurnRate`

## Mitigation

- Injection self-terminated after 3 waves (30 total requests)
- The mock model handled garbage prompts gracefully (returned valid responses with reasonable quality scores)
- Only `fail=true` requests actually triggered errors — the model is robust to weird input

## Root Cause

Two-pronged attack simulation:
1. **Garbage prompts:** Overlong strings, special characters, injection attempts — the mock model processed them without error
2. **Forced failures:** `fail=true` parameter caused 503 responses — simulating a backend that's actively rejecting requests

The model's robustness to garbage input is a *good sign* — it means input validation isn't the weak point. The real vulnerability is backend availability.

## Action Items

1. ✅ **Implemented:** Error rate alerting catches this scenario
2. 📋 **TODO:** Add input validation layer — reject prompts > 2000 chars, detect injection patterns
3. 📋 **TODO:** Add quality_score monitoring — alert when average quality drops below 0.5 over 5 minutes
4. 📋 **TODO:** Implement rate limiting per client — prevent a single source from flooding with poison
5. 📋 **TODO:** Add prompt sanitization for control characters

## Lessons Learned

- The mock model is surprisingly robust to garbage input — real models might not be
- `fail=true` is a clean way to simulate backend degradation without modifying the model code
- Quality score didn't drop for garbage prompts (always ~0.8) — this suggests the mock quality scoring is too generous; a real quality metric would catch nonsense responses
- The 0.05/s threshold is sensitive enough to catch a sustained poisoning attack but would ignore a few stray bad requests
