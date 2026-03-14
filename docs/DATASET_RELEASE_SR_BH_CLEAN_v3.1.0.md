# Dataset Release: SRBH_clean_v3.1.0

Status note
-----------
This file is a dataset release note. It documents the cleaned dataset snapshot and its provenance.
Current application/runtime status is tracked separately in `docs/CONTEXT.md`.

Summary
-------
- **Dataset**: SRBH_clean_v3.1.0
- **Produced by**: `data/clean_907k.py` (pipeline v3.1.0)
- **Date**: 2026-03-11

Key Configuration
-----------------
- MinHash threshold: **0.85**
- Shingle size: 5
- MinHash permutations: 128
- Cluster cap: **100** (stratified sampling within clusters)

Primary Statistics
------------------
- Total rows (final exported): **199,039**
- Total clusters: **96,843**
- Singleton ratio (clusters size==1): **78.6%**
- Largest cluster (after cap): **101**
- Cross-split leakage: **0%** (no exact duplicates or cluster overlaps across splits)

Provenance & Repro
------------------
- Pipeline version: `3.1.0` (see `data/clean_907k.py`)
- Audit script: `data/dataset_audit.py` — audit passed on export
- Repro commands:

```bash
python data/clean_907k.py
python data/dataset_audit.py
```

Artifacts
---------
- Exported Parquet (train/validation/test): `data/processed/v3_907k_cleaned/`
- Audit log: `data/processed/v3_907k_cleaned/audit_log.json`
- Cluster-size histogram: `data/processed/v3_907k_cleaned/cluster_size_hist.png`

Notes & Rationale
-----------------
- Raised MinHash threshold and applied cluster capping to eliminate megacluster-driven
  split degeneracy and leakage. This reduces training/test contamination risk at the
  cost of removing repeated scanner payloads (≈140k rows removed during capping).
- Quarantine rules were tightened (context-sensitive shell patterns) to reduce
  false positives in Normal-class quarantine.

Recommended next steps
----------------------
- Commit these changes and tag the release (e.g., `dataset/v3.1.0`).
- Retain a copy of the pre-cap dataset snapshot if you want to analyze scanner traffic
  separately.

Current repo limitation
-----------------------
- The release artifacts are current, but the preprocessing scripts are still developer-workstation oriented and are not yet fully repo-relative for general reruns.

Contact
-------
For questions about preprocessing choices, inspect `data/clean_907k.py`, `data/dataset_audit.py`, and the baseline summary in `docs/DATASET_BASELINE_SR_BH_v3.1.0.md`.
