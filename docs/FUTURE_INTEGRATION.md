# Project Target Integration Architectural Guide

This guide details the integration topology and sandbox metadata parameters of the Land Records Portal.

---

## Architecture Placement

In a live production or development lab setup, the **Land Records Portal** acts as the downstream application behind a reverse proxy or inspection layer. This configuration operates inside your sandbox machine or Kubernetes pod.

```
       [ Public Browser / Penetration Script / Pentester ]
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │       Nginx / Apache Proxy           │
            │      with inspection rules           │
            └──────────────────────────────────────┘
                               │
                Ingests proxy logs for analysis
                               │ (Syslog / Filebeat log forwarding)
                               ▼
                    ┌──────────────────────┐
                    │   Analysis System    │
                    │   and Dashboard      │
                    └──────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │   Downstream Next.js Target Portal   │
            │             (This App)               │
            └──────────────────────────────────────┘
```

The portal itself does **not** process, block, or alert on threats. This separation isolates application logic from the inspection layer.

---

## Log Ingestion and Processing Flow

1. **Local Request Dispatch:** The user or testing script submits an exploit vector or mock transaction to `http://localhost:3000`.
2. **Reverse Proxy Inspection:** A proxy or inspection layer can scan incoming query parameters and POST bodies.
3. **Downstream Forward:** If the proxy runs in detection-only mode, the request passes through to the Next.js portal. If custom audit headers are injected (e.g. `x-demo-trace-id` or `x-request-id`), the portal can capture them.
4. **Proxy Logging:** The proxy appends alert metadata to its log stream.
5. **Aggregation:** Log collectors can stream these logs to an analysis endpoint.
6. **Triage:** The analysis system can cross-reference `x-demo-trace-id` values and categorize events.
7. **Dashboard:** Real-time visual cards can populate a local dashboard.

---

## Custom Auditing / Telemetry Headers

The portal inspects several standard headers inside `/lib/request-metadata.ts` to aid testing and tracing across log layers:

* **`x-demo-trace-id`:** Assigned by security scripts or proxy middleware to represent a specific transaction stream.
* **`x-request-id`:** Auto-assigned correlation identifier for web traffic path analysis.
* **`x-forwarded-for`:** Preserves the actual origin IP address when traffic is proxied.
* **`user-agent`:** Useful for tracking testing agents.

These headers can be populated manually inside transaction status updates or support desk routes to verify log alignment.

---

## Safe Sandbox Boundaries

To prevent vulnerabilities in the local laboratory container, the portal has:

* **Standard Character Escaping:** Every dynamic input displayed (e.g. in home or comment boards) is escaped before rendering.
* **Strict Path Sanitization:** No inputs directly access native Node.js routing or file-system primitives.
* **Database Writes:** User submissions are stored in the local Prisma/SQLite database for demo purposes.
