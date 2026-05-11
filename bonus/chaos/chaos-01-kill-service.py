"""
Chaos #1: Kill the FastAPI inference service.
Simulates: process crash, OOM kill, or container failure.
Expected signal: Prometheus target down, inference_requests_total stops,
  SLO burn-rate alert fires.
"""
import subprocess
import time
import sys
import json
import urllib.request

SERVICE = "app"
COMPOSE_FILE = "docker-compose.yml"


def check_health():
    """Check if the app is responding."""
    try:
        req = urllib.request.urlopen("http://localhost:8000/healthz", timeout=3)
        return req.status == 200
    except Exception:
        return False


def check_prometheus_up():
    """Check if Prometheus sees the target as up."""
    try:
        req = urllib.request.urlopen(
            "http://localhost:9090/api/v1/query?query=up{job='fastapi-app'}",
            timeout=5,
        )
        data = json.loads(req.read())
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1]) == 1.0
        return False
    except Exception:
        return False


def main():
    print("=" * 60)
    print("CHAOS #1: Kill FastAPI inference service")
    print("=" * 60)

    # Pre-flight
    print("\n[PRE] Checking service health...")
    if not check_health():
        print("[ERROR] Service is not healthy before injection. Aborting.")
        sys.exit(1)
    print("[PRE] Service is healthy.")

    # Inject failure
    print(f"\n[INJECT] Stopping container: {SERVICE}")
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "stop", SERVICE],
        check=True,
    )
    inject_time = time.time()
    print(f"[INJECT] Container stopped at {time.strftime('%H:%M:%S')}")

    # Monitor detection
    print("\n[MONITOR] Waiting for detection signals...")
    detected = False
    for i in range(60):  # Wait up to 5 minutes
        time.sleep(5)
        elapsed = time.time() - inject_time

        health = check_health()
        prom_up = check_prometheus_up()

        print(
            f"  [{elapsed:.0f}s] healthz={health}  prometheus_up={prom_up}"
        )

        if not prom_up and not detected:
            detected = True
            detect_time = elapsed
            print(f"\n  >>> DETECTED at {detect_time:.0f}s — Prometheus target is DOWN")

        if detected and elapsed > 30:
            break

    # Recover
    print(f"\n[RECOVER] Starting container: {SERVICE}")
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "start", SERVICE],
        check=True,
    )
    time.sleep(5)

    if check_health():
        print("[RECOVER] Service is healthy again.")
    else:
        print("[RECOVER] WARNING: Service did not recover!")

    print(f"\n[RESULT] Time to detect: {detect_time:.0f}s" if detected else "\n[RESULT] NOT DETECTED within window")
    print("=" * 60)


if __name__ == "__main__":
    main()
