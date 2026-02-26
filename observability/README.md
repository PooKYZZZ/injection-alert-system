# Observability Layer

This directory is a **first-class architectural layer** — not a log dump.

## Purpose

Provides structural representation for runtime system health, automated mitigation telemetry, and human-in-the-loop visibility — all critical behaviors for a confidence-gated WAF+ML system.

## Directory Map

```
observability/
├── metrics/     # Prometheus scrape configuration and metric endpoint definitions
│                # Tracks: request volume, WAF block rate, ML confidence distribution,
│                # retraining pipeline health, model drift indicators
│
├── alerts/      # Alert rule definitions
│                # Triggers: confidence below threshold, WAF anomaly rate spike,
│                # retraining failure, model rollback event, audit log gap
│
└── dashboards/  # Grafana JSON exports (or equivalent)
                 # Panels: live threat dashboard, confidence score histogram,
                 # 20-day retraining cycle tracker, human review queue depth
```

## Architectural Justification

The system claims **automated confidence-gated mitigation** and **human-in-the-loop review**. Without observability structure, these claims are architecturally unsubstantiated. This layer provides the structural evidence that the system can be monitored, governed, and defended.
