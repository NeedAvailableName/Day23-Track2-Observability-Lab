# Bonus Reflection — Postmortem Rehearsal (Provocation #5)

## What surprised me?

**Detection speed exceeded expectations.** I expected the kill-service chaos to take 15-30 seconds to detect (Prometheus scrape interval + alert evaluation). In reality, the `up` metric dropped to 0 on the very first scrape after the kill — 5 seconds flat. The burn-rate alerts need more accumulation (2+ minutes), but the raw `up` signal is immediate. This taught me that *which metric you watch* matters more than *how fast your alert evaluates*. A simple boolean health check beat a sophisticated multi-window burn-rate calculation for acute failures.

**The mock model was surprisingly robust to garbage input.** Chaos #3 (data poisoning) sent control characters, 500-character strings, and injection attempts. The mock model processed every single one without error — it even returned quality scores of ~0.8 for nonsense. A real model might not be this forgiving. This made me realize that input validation is a *separate layer* you need to build; you can't rely on the model to reject bad input.

**Error rate decay was natural and fast.** After each chaos injection stopped, the error rate dropped to zero within 60 seconds without any manual intervention. The system is self-healing for transient issues — the risk is sustained degradation, not momentary blips.

## What would you build next if you had another 8 hours?

1. **Circuit breaker on the inference client.** After N consecutive failures, stop sending traffic for 30 seconds, then probe with a single request. This prevents thundering herd during recovery and reduces wasted compute on requests that will fail.

2. **Input validation middleware.** Reject prompts > 2000 characters, strip control characters, detect common injection patterns ("ignore previous instructions", etc.). Log rejected requests as a separate metric so we can track attack volume.

3. **Quality score anomaly detection.** The current alerting only watches error rates. But the most dangerous failure is *wrong answers that don't error*. I'd add a rolling average quality_score alert: if avg(quality_score) over 5 minutes drops below 0.6, fire a warning. This catches the "model is returning garbage but HTTP 200" scenario.

4. **Runbook automation.** The postmortems have clear action items — "restart service", "check GPU memory", "review recent deployments". I'd wire the top 3 alerts to auto-remediation scripts (restart container, scale up replicas, roll back last deploy) with a human-in-the-loop approval step.

5. **Load testing with realistic traffic patterns.** The chaos scripts use uniform concurrent requests. Real traffic has diurnal patterns, bursty arrivals, and correlated retries. I'd use Locust with a realistic user model to find the *actual* breaking point, not the synthetic one.

## Bonus deliverables summary

| File | Description |
|------|-------------|
| `bonus/chaos/chaos-01-kill-service.py` | Kill FastAPI container, measure time-to-detect |
| `bonus/chaos/chaos-02-inject-latency.py` | Traffic spike + forced failures |
| `bonus/chaos/chaos-03-poison-data.py` | Garbage prompts + forced failures |
| `bonus/postmortems/incident-01.md` | Postmortem: service crash (detected in 5s) |
| `bonus/postmortems/incident-02.md` | Postmortem: error spike (detected in 20s) |
| `bonus/postmortems/incident-03.md` | Postmortem: data poisoning (detected in 20s) |
| `bonus/REFLECTION.md` | This file |

**Real change implemented:** Added `InferenceErrorSpike` alert rule to `slo-burn-rate.yml` — catches acute error bursts within 30 seconds, complementing the existing burn-rate alerts that need sustained degradation. Reloaded Prometheus to activate.
