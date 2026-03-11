# Dataset Baseline: SRBH_clean_v3.1.0

This document captures the frozen training metadata used for baseline training.

Summary
-------
- Dataset version: SRBH_clean_v3.1.0
- Pipeline version: 3.1.0
- Git commit: `339883bf3efcc3799fbccb9a4c2947ae0661950d`
- Date generated: 2026-03-11T06:13:16.379803+00:00
- Tokenizer: distilbert-base-uncased

Key statistics (from `data/processed/v3_907k_cleaned`)
-------------------------------------------------------
- Initial raw rows: 907,815
- After dedup + near-dup cap: 199,039
- Train / Val / Test: 159,873 / 19,661 / 19,505
- Quarantined (suspicious benign): 23,826
- Total near-dup clusters: 96,843  |  singleton ratio: 78.6 %
- Largest cluster (before cap): 13,969  |  after cap (≤ 100): 101
- Cross-split leakage: 0 %

Preprocessing parameters
------------------------
| Parameter              | Value |
|------------------------|-------|
| MinHash threshold      | 0.85  |
| Shingle size           | 5     |
| MinHash num_perm       | 128   |
| MAX_CLUSTER_SIZE       | 100   |
| SPLIT_CANDIDATE_SEEDS  | 5     |
| Split seed (chosen)    | 42    |

Per-split class distribution
-----------------------------
### Train (159,873 rows)
| Class          | Count  | %     |
|----------------|--------|-------|
| SQL Injection  | 74,723 | 46.74 |
| Other Attacks  | 49,546 | 30.99 |
| Normal         | 29,991 | 18.76 |
| Code Injection |  5,613 |  3.51 |

### Validation (19,661 rows)
| Class          | Count  | %     |
|----------------|--------|-------|
| SQL Injection  |  9,138 | 46.48 |
| Other Attacks  |  5,982 | 30.43 |
| Normal         |  3,864 | 19.65 |
| Code Injection |    677 |  3.44 |

### Test (19,505 rows)
| Class          | Count  | %     |
|----------------|--------|-------|
| SQL Injection  |  8,975 | 46.01 |
| Other Attacks  |  6,035 | 30.94 |
| Normal         |  3,658 | 18.75 |
| Code Injection |    837 |  4.29 |

Payload length (chars)
-----------------------
| Split      | Mean  | Median | p95 | p99 | Max |
|------------|-------|--------|-----|-----|-----|
| Train      |  98.2 |   87   | 224 | 295 | 573 |
| Validation |  96.1 |   87   | 217 | 290 | 632 |
| Test       | 100.5 |   87   | 233 | 310 | 538 |

Token-length summary — `distilbert-base-uncased`
-------------------------------------------------
| Split      | n       | Mean  | Median | p95 | p99 | Max |
|------------|---------|-------|--------|-----|-----|-----|
| Train      | 159,873 | 52.35 |   46   | 113 | 154 | 267 |
| Validation |  19,661 | 51.59 |   46   | 112 | 145 | 287 |
| Test       |  19,505 | 53.60 |   47   | 119 | 161 | 250 |

**Recommended `max_seq_len`:** 128 covers the 95th percentile for all splits; 256 covers >99 %.

Files created
-------------
- `data/processed/v3_907k_cleaned/checksums.txt` — SHA256 of 4 canonical parquets
- `data/processed/v3_907k_cleaned/metadata_preprocessing.json` — preprocessing params + git commit
- `data/processed/v3_907k_cleaned/training_metadata.json` — per-split class/payload stats
- `data/processed/v3_907k_cleaned/tokenizer_lengths_{train,validation,test}.json` — token-length summaries
- `data/processed/v3_907k_cleaned/tokenizer_lengths_{train,validation,test}.csv` — full per-row token counts
- `data/processed/v3_907k_cleaned/cluster_size_hist.png` — near-dup cluster size histogram
- `docs/DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md` — release note

Repro
-----
```bash
python scripts/create_checksums.py
python scripts/generate_preprocessing_metadata.py
python scripts/compute_training_metadata.py
python scripts/tokenize_and_compute_lengths.py --tokenizer distilbert-base-uncased --input data/processed/v3_907k_cleaned/train.parquet
python scripts/tokenize_and_compute_lengths.py --tokenizer distilbert-base-uncased --input data/processed/v3_907k_cleaned/validation.parquet
python scripts/tokenize_and_compute_lengths.py --tokenizer distilbert-base-uncased --input data/processed/v3_907k_cleaned/test.parquet
```
