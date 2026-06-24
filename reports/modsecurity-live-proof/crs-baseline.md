# CRS-only Baseline Evidence Report

**Project:** CyberTrace / Injection Alert System
**Report type:** Local CRS-only baseline evidence
**WAF path:** `http://localhost:8088`
**Audit log:** `logs/modsecurity/modsec_audit.jsonl`
**Audit format:** JSONL
**Date/time:** `2026-06-24 17:59:04 +08:00`
**Git commit:** `53257fe`

---

## 1. Purpose

This report records observed ModSecurity / OWASP Core Rule Set behavior before relying on ML triage or dashboard interpretation.

The goal is to prove that the WAF rule layer was tested separately.

This report checks:

* normal traffic passes through the WAF
* SQL injection-looking traffic is blocked
* XSS-looking traffic is blocked
* command/file-access-like traffic is blocked
* a simple weird-but-legitimate query does not trigger a false positive

This is a small local baseline only. It is not a full WAF certification.

---

## 2. Environment

| Item                                   | Value                                 |
| -------------------------------------- | ------------------------------------- |
| WAF proof path                         | `http://localhost:8088`               |
| ModSecurity audit log                  | `logs/modsecurity/modsec_audit.jsonl` |
| Audit format                           | JSONL                                 |
| Source IP observed from Docker network | `172.21.0.1`                          |
| CRS paranoia level observed from tags  | `paranoia-level/1`                    |
| Backend proof path                     | Docker-internal only                  |
| Full SIEM/Wazuh deployment             | Not implemented                       |
| Production WAF claim                   | Not claimed                           |

---

## 3. Summary Table

| Test                     | Request                                             | Expected | Actual HTTP | Transaction ID        | CRS Rule IDs                           | Verdict |
| ------------------------ | --------------------------------------------------- | -------: | ----------: | --------------------- | -------------------------------------- | ------- |
| Normal WAF health        | `/healthz`                                          |      200 |         200 | N/A                   | N/A                                    | PASS    |
| Normal API health        | `/api/health`                                       |      200 |         200 | N/A                   | N/A                                    | PASS    |
| SQLi                     | `/api/health?id=31%27%20OR%2031%3D31--`             |      403 |         403 | `178229498739.243683` | `942100`, `949110`                     | PASS    |
| XSS-like                 | `/api/health?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E` |  Observe |         403 | `178229499493.508650` | `941100`, `941110`, `941160`, `949110` | PASS    |
| Command/file-access-like | `/api/health?cmd=cat%20%2Fetc%2Fpasswd`             |  Observe |         403 | `178229500217.332219` | `930120`, `932160`, `949110`           | PASS    |
| Weird legitimate query   | `/api/health?search=team-27_status_ok_2026`         |      200 |         200 | N/A                   | N/A                                    | PASS    |

---

## 4. Observed CRS Evidence

### 4.1 SQL Injection Test

Request:

```text
/api/health?id=31%27%20OR%2031%3D31--
```

Observed result:

```text
HTTP status: 403
transaction_id: 178229498739.243683
source_ip: 172.21.0.1
request_uri: /api/health?id=31%27%20OR%2031%3D31--
```

Triggered CRS rules:

```text
942100
949110
```

Matched messages:

```text
SQL Injection Attack Detected via libinjection
Inbound Anomaly Score Exceeded (Total Score: 5)
```

Relevant tags observed:

```text
attack-sqli
paranoia-level/1
OWASP_CRS
capec/1000/152/248/66
```

Interpretation:

```text
CRS blocked the SQL injection-looking request at the WAF layer.
```

---

### 4.2 XSS-like Test

Request:

```text
/api/health?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E
```

Observed result:

```text
HTTP status: 403
transaction_id: 178229499493.508650
source_ip: 172.21.0.1
request_uri: /api/health?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E
```

Triggered CRS rules:

```text
941100
941110
941160
949110
```

Matched messages:

```text
XSS Attack Detected via libinjection
XSS Filter - Category 1: Script Tag Vector
NoScript XSS InjectionChecker: HTML Injection
Inbound Anomaly Score Exceeded (Total Score: 15)
```

Relevant tags observed:

```text
attack-xss
paranoia-level/1
OWASP_CRS
capec/1000/152/242
```

Interpretation:

```text
CRS blocked the XSS-looking request at the WAF layer.
```

---

### 4.3 Command/File-access-like Test

Request:

```text
/api/health?cmd=cat%20%2Fetc%2Fpasswd
```

Observed result:

```text
HTTP status: 403
transaction_id: 178229500217.332219
source_ip: 172.21.0.1
request_uri: /api/health?cmd=cat%20%2Fetc%2Fpasswd
```

Triggered CRS rules:

```text
930120
932160
949110
```

Matched messages:

```text
OS File Access Attempt
Remote Command Execution: Unix Shell Code Found
Inbound Anomaly Score Exceeded (Total Score: 10)
```

Relevant tags observed:

```text
attack-lfi
attack-rce
paranoia-level/1
OWASP_CRS
capec/1000/255/153/126
capec/1000/152/248/88
```

Interpretation:

```text
CRS blocked the command/file-access-looking request at the WAF layer.
```

---

## 5. Findings

* Normal WAF health traffic returned `200`.
* Normal backend health traffic through the WAF returned `200`.
* SQLi-looking traffic returned `403` and triggered CRS SQLi detection.
* XSS-looking traffic returned `403` and triggered CRS XSS detection.
* Command/file-access-like traffic returned `403` and triggered CRS LFI/RCE-related detection.
* The simple weird-but-legitimate query returned `200`, so this small false-positive check passed.
* Observed CRS tags show `paranoia-level/1`.

---

## 6. Interpretation

CRS is the rule-based WAF layer.

In this baseline, CRS blocked the tested attack-looking requests before they were treated as normal backend traffic.

ML triage and dashboard display are separate from this report.

Correct claim:

```text
ModSecurity / OWASP CRS blocked the tested attack-looking requests. CyberTrace can then ingest, classify, store, and display the resulting security event.
```

Incorrect claim:

```text
The ML model blocked the attack.
```

---

## 7. Limitations

This report has important limits:

* This is a small local CRS baseline, not a full WAF certification.
* This does not prove every SQLi payload is blocked.
* This does not prove every XSS payload is blocked.
* This does not prove every command injection, RCE, or file access payload is blocked.
* This does not replace CRS tuning.
* This does not replace false-positive testing using real application traffic.
* This does not claim production deployment.
* This does not claim full SIEM/Wazuh deployment.
* This does not claim centralized production log retention.

---

## 8. Result

```text
PASS: Normal traffic passed.
PASS: SQLi-looking traffic was blocked by CRS.
PASS: XSS-looking traffic was blocked by CRS.
PASS: Command/file-access-like traffic was blocked by CRS.
PASS: Simple false-positive check passed.
WARN: This is a small controlled local baseline only.
```
