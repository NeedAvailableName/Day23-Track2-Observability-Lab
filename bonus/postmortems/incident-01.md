# Incident-01: FastAPI Inference Service Crash

**Date:** 2026-05-11
**Duration:** ~5 minutes
**Severity:** Critical
**Detection time:** 5 seconds

---

## Timeline

| Time | Event |
|------|-------|
| T+0s | Chaos injection: `docker compose stop app` — inference service killed |
| T+5s | Prometheus `up{job='fastapi-app'}` drops to 0 — **DETECTED** |
| T+5s | Prometheus scrape shows target as DOWN |
| T+60s | Recovery initiated: `docker compose start app` |
| T+65s | Service healthy again, `/healthz` returns 200 |

## Detection

- **Signal:** Prometheus `up` metric for `fastapi-app` target dropped from 1 to 0
- **Time to detect:** 5 seconds (limited by Prometheus scrape interval of 5s)
- **Alert rule:** `SLO_InferenceAvailability_BurnRate` — multi-window burn-rate (5m/1h and 30m/6h)

## Mitigation

- Restarted the container via `docker compose start app`
- Service recovered within 5 seconds of restart
- No data loss (stateless service)

## Root Cause

The FastAPI process inside the container exited (simulated OOM/crash). Docker detected the exit and marked the container as stopped. Prometheus's scrape failure triggered the `up` metric to 0.

## Action Items

1. ✅ **Implemented:** Added `restart: unless-stopped` to docker-compose.yml for the app service — ensures automatic restart on crash
2. 📋 **TODO:** Add container health check with `HEALTHCHECK` directive in Dockerfile for faster Docker-level detection
3. 📋 **TODO:** Configure Alertmanager PagerDuty integration for production on-call paging

## Lessons Learned

- 5-second detection is excellent — limited only by Prometheus scrape interval
- The multi-window burn-rate alert correctly avoids false positives from brief blips
- A stateless service recovers trivially; the real risk is *not knowing* it went down
