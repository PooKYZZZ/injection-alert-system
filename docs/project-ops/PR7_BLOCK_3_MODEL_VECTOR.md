# PR7 Block 3 real-model vector

Status: `PASS` for deterministic real-model vector selection; this document does
not claim the full attack-to-WAF lifecycle is complete.

## Pinned input

```text
GET /records/search?id=1%20OR%201=1-- HTTP/1.1
Host: localhost
```

The application applies the existing `preprocess_http_request()` path before
inference. The raw request remains the persisted evidence; preprocessing is
model-input-only.

## Artifact and policy

| Field | Value |
|---|---|
| Artifact directory | `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755` |
| Model version | `distilbert_v3_907k_cleaned_20260312_133755` |
| Checkpoint SHA-256 | `8f43f4e85a4c728ea24aff7c1d0e453661f1257252cd62845bd5051120eb21a2` |
| Temperature | `0.596868` |
| Critical threshold | `0.90` |
| Labels | `Code Injection`, `Normal`, `Other Attacks`, `SQL Injection` |
| Runtime device | CPU |

## Observed result

Run date: 30 July 2026, local controlled environment.

| Prediction | Confidence | Tier | Model version |
|---|---:|---|---|
| `SQL Injection` | `0.998841` | `CRITICAL` | `distilbert_v3_907k_cleaned_20260312_133755` |

The result was obtained with the real packaged model, not the mock classifier.
The guarded regression is `tests/ml/test_pr7_critical_vector.py` and runs with:

```powershell
$env:PR7_RUN_REAL_MODEL = "1"
.venv\Scripts\python.exe -m pytest -q tests/ml/test_pr7_critical_vector.py
```

This vector proves only model selection and target-path compatibility. It does
not prove source verification, bridge delivery, PR7 state mutation, WAF
activation, causality, revocation, expiry, or no-upstream behaviour.
