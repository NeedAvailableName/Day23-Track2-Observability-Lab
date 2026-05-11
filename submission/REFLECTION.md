# Day 23 Lab Reflection

> Fill in each section. Grader reads the "What I'd change" paragraph closest.

**Student:** Phạm Hải Đăng
**Submission date:** 2026-05-11
**Lab repo URL:** https://github.com/NeedAvailableName/Day23-Track2-Observability-Lab

---

## 1. Hardware + setup output

Paste output of `python3 00-setup/verify-docker.py`:

```
Docker:        OK  (29.3.1)
Compose v2:    OK  (5.1.1)
RAM available: 7.39 GB (OK)
Ports free:    OK
Report written: C:\Code\VIN_AI\Labs\Day23-Track2-Observability-Lab\00-setup\setup-report.json
```

---

## 2. Track 02 — Dashboards & Alerts

### 6 essential panels (screenshot)

Drop `submission/screenshots/dashboard-overview.png`.

### Burn-rate panel

Drop `submission/screenshots/slo-burn-rate.png`.

### Alert fire + resolve

| When | What | Evidence |
|---|---|---|
| _T0_ | killed `day23-app`         | screenshot `alertmanager-firing.png` |
| _T0+90s_ | `ServiceDown` fired   | screenshot `slack-firing.png` |
| _T1_ | restored app              | — |
| _T1+60s_ | alert resolved        | screenshot `slack-resolved.png` |

### One thing surprised me about Prometheus / Grafana

The dashboards automatically load when placing the JSON files in the dashboards provisioning directory. It eliminates manual setup steps.

---

## 3. Track 03 — Tracing & Logs

### One trace screenshot from Jaeger

Drop `submission/screenshots/jaeger-trace.png` showing `embed-text → vector-search → generate-tokens` spans.

### Log line correlated to trace

Paste the log line and the trace_id it links to:

```json
{"model": "llama3-mock", "input_tokens": 4, "output_tokens": 54, "quality": 0.82, "duration_seconds": 0.1777, "trace_id": "cda362afe3aa05b776e12599cecbaaad", "event": "prediction served", "level": "info", "timestamp": "2026-05-11T03:38:18.591437Z"}
```

### Tail-sampling math

If your service produced N traces/sec, what fraction did the policy keep? Show the calculation.

The policy keeps 100% of errors and slow requests (>2000ms), and probabilistically samples 1% of the remaining healthy requests.
Therefore, if there are E errors/slow requests per second, the fraction kept is:
`(E + (N - E) * 0.01) / N`

---

## 4. Track 04 — Drift Detection

### PSI scores

Paste `04-drift-detection/reports/drift-summary.json`:

```json
{
  "prompt_length": {
    "psi": 3.461,
    "kl": 1.7982,
    "ks_stat": 0.702,
    "ks_pvalue": 0.0,
    "drift": "yes"
  },
  "embedding_norm": {
    "psi": 0.0187,
    "kl": 0.0324,
    "ks_stat": 0.052,
    "ks_pvalue": 0.133853,
    "drift": "no"
  },
  "response_length": {
    "psi": 0.0162,
    "kl": 0.0178,
    "ks_stat": 0.056,
    "ks_pvalue": 0.086899,
    "drift": "no"
  },
  "response_quality": {
    "psi": 8.8486,
    "kl": 13.5011,
    "ks_stat": 0.941,
    "ks_pvalue": 0.0,
    "drift": "yes"
  }
}
```

### Which test fits which feature?

For each of `prompt_length`, `embedding_norm`, `response_length`, `response_quality`, name the test (PSI / KL / KS / MMD) you'd choose in production and why.

- **prompt_length**: PSI (Population Stability Index), because it's good for assessing shift in categorical or binned discrete distributions and provides a reliable score for data drift.
- **embedding_norm**: KS (Kolmogorov-Smirnov), because it's effective for continuous numerical distributions and detecting shape changes in embeddings.
- **response_length**: PSI, as we usually bucket lengths (e.g. short, medium, long) to evaluate drift in LLM output verbosity.
- **response_quality**: KL (Kullback-Leibler divergence), useful for evaluating shifts in expected probability distributions or scores over time.

---

## 5. Track 05 — Cross-Day Integration

### Which prior-day metric was hardest to expose? Why?

The hardest metric to expose was LLM quality score (inference_quality_score) because determining "quality" in real-time requires LLM-as-a-judge or human feedback which introduces significant latency, forcing us to use delayed asynchronous metrics or proxies.

---

## 6. The single change that mattered most

> **Grader reads this closest.** What one thing about your stack design — a metric you added, a label you dropped, a panel you reorganized, an alert threshold you tuned — made the biggest difference between "works" and "useful"? Write 1-2 paragraphs. Connect it to a concept from the deck.

The single most impactful change was hardcoding the Slack webhook URL properly so that Alertmanager could actually trigger alerts to our on-call channels, transforming our setup from a passive "works" dashboard to a "useful" proactive monitoring system. By receiving the Slack notifications for `ServiceDown`, we close the loop in the RED/USE observability strategy discussed in the deck. We don't just rely on someone looking at the Grafana dashboard; the system actively notifies the correct team when SLIs breach SLOs.

Additionally, ensuring that the tail-sampling policy in the OpenTelemetry Collector retained 100% of errors while sampling 1% of healthy traffic struck the perfect balance. This configuration (from the tracing and sampling slides in the deck) allowed us to retain full visibility into failed or severely delayed LLM inferences without overwhelming Jaeger with the storage cost of normal traffic. This made debugging the AI pipeline significantly easier.
