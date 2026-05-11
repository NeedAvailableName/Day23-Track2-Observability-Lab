"""
Chaos #2: Saturate the inference service + inject failures.
Simulates: traffic spike with degraded backend (model returning errors).
Expected signal: error rate spikes, inference_requests_total{status="error"} increases,
  SLO burn-rate alert fires.
"""
import json
import time
import urllib.request
import concurrent.futures

PREDICT_URL = "http://localhost:8000/predict"
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"


def query_prometheus(expr):
    try:
        url = f"{PROMETHEUS_URL}?query={expr}"
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read())
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
        return None
    except Exception:
        return None


def send_request(i, fail=False):
    """Send a single predict request, return (latency, status_code)."""
    try:
        body = {"prompt": f"load test request {i}", "fail": fail}
        req = urllib.request.Request(
            PREDICT_URL,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=30)
        latency = time.time() - start
        return (latency, resp.status)
    except urllib.error.HTTPError as e:
        return (time.time() - start, e.code)
    except Exception:
        return (-1, 0)


def main():
    print("=" * 60)
    print("CHAOS #2: Traffic spike + forced failures")
    print("=" * 60)

    # Pre-flight
    print("\n[PRE] Baseline metrics...")
    baseline_err = query_prometheus("rate(inference_requests_total{status='error'}[5m])")
    baseline_total = query_prometheus("rate(inference_requests_total[5m])")
    baseline_p95 = query_prometheus(
        "histogram_quantile(0.95,rate(inference_latency_seconds_bucket[1m]))"
    )
    print(f"[PRE] Error rate: {baseline_err or 0:.4f}/s")
    print(f"[PRE] Total rate: {baseline_total or 0:.4f}/s")
    print(f"[PRE] p95 latency: {baseline_p95 or 0:.4f}s")

    # Phase 1: Normal load spike (no failures)
    print("\n[PHASE 1] Normal traffic spike (20 concurrent × 3 waves)...")
    for wave in range(3):
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_request, i, False) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        valid = [r[0] for r in results if r[0] > 0]
        errors = sum(1 for r in results if r[1] >= 400 or r[0] < 0)
        avg = sum(valid) / len(valid) if valid else 0
        print(f"  Wave {wave+1}: avg={avg:.3f}s  errors={errors}/20")

    # Phase 2: Spike with forced failures (simulating backend degradation)
    print("\n[PHASE 2] Traffic spike WITH forced failures (fail=true)...")
    inject_time = time.time()
    detected = False
    detect_time = None

    for wave in range(5):
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Mix: 50% normal, 50% forced failures
            futures = []
            for i in range(20):
                futures.append(executor.submit(send_request, i, fail=(i % 2 == 0)))
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        valid = [r[0] for r in results if r[0] > 0]
        errors = sum(1 for r in results if r[1] >= 400 or r[0] < 0)
        avg = sum(valid) / len(valid) if valid else 0
        elapsed = time.time() - inject_time
        print(f"  Wave {wave+1}: avg={avg:.3f}s  errors={errors}/20  [{elapsed:.0f}s]")

        # Check Prometheus
        err_rate = query_prometheus("rate(inference_requests_total{status='error'}[1m])")
        if err_rate and err_rate > 0.1 and not detected:
            detected = True
            detect_time = elapsed
            print(f"\n  >>> DETECTED at {detect_time:.0f}s — error rate {err_rate:.4f}/s > 0.1/s")

    # Monitor recovery
    print("\n[MONITOR] Checking recovery (30s)...")
    for i in range(6):
        time.sleep(5)
        elapsed = time.time() - inject_time
        err_rate = query_prometheus("rate(inference_requests_total{status='error'}[1m])")
        total_rate = query_prometheus("rate(inference_requests_total[1m])")
        print(f"  [{elapsed:.0f}s] error_rate={err_rate or 0:.4f}  total_rate={total_rate or 0:.4f}")

    print(f"\n[RESULT] Time to detect: {detect_time:.0f}s" if detected else "\n[RESULT] NOT DETECTED within window")
    print("=" * 60)


if __name__ == "__main__":
    main()
