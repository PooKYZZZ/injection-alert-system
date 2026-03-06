# SR-BH 2020 HTTP Attack Dataset - Pipeline Execution Audit Report

**Report Generated:** 2026-03-04  
**Pipeline Version:** 2.0.0  
**Dataset:** 907k CAPEC Multi-label HTTP Attack Dataset  
**Output Directory:** `injection-alert-system/data/processed/v3_907k_cleaned/`

---

## Executive Summary

The dataset cleaning pipeline (`clean_907k.py`) executed successfully, processing 907,815 raw HTTP request records and producing a cleaned dataset of 327,755 unique payloads suitable for transformer-based Web Application Firewall (WAF) training.

### Unicode Encoding Error - Impact Assessment

During execution, a Unicode encoding error occurred at line 309 of `clean_907k.py`:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 2: 
character maps to <undefined>
```

**Root Cause:** The Windows cp1252 console encoding cannot represent the Unicode checkmark character (✓, U+2713).

**Impact:** **NONE** - The error occurred **after** all data processing was complete:
- All parquet files were successfully written
- The audit log (`audit_log.json`) was serialized and saved
- Dataset splits were created and verified
- The error only affected the final console output message

**Remediation:** The checkmark character was replaced with `[OK]` to ensure cross-platform compatibility.

**Output Integrity:** ✅ **VERIFIED** - All 6 output files are complete and valid.

---

## Technical Implementation

### Pipeline Architecture

The cleaning pipeline implements a 10-stage processing workflow:

| Stage | Description | Implementation |
|-------|-------------|----------------|
| 1 | Dataset Loading | `pandas.read_csv()` with low_memory=False |
| 2 & 3 | Canonicalization & Malformed Removal | URL decode, HTML unescape, Unicode NFKC normalization |
| 4 | Exact Duplicate Removal | SHA256 hash-based deduplication |
| 7 | CAPEC Label Mapping | Priority-based 4-class classification |
| 6 | Benign Quarantine | Regex-based suspicious pattern detection |
| 5 | Near-Duplicate Analysis | MinHash LSH with 0.90 threshold |
| 8 | Statistics Tracking | Payload length and token estimation |
| 9 | Stratified Splitting | 80/10/10 train/val/test split |
| 10 | Audit Log Export | JSON serialization with SHA256 checksums |

### CAPEC Label Mapping Configuration

The pipeline implements deterministic CAPEC-to-class mapping:

```python
Priority Order:
1. CAPEC-66  → SQL Injection
2. CAPEC-242 → Code Injection
3. All other CAPECs → Other Attacks
4. CAPEC-000 → Normal
```

**Important Note:** The source dataset contains only 3 CAPEC types (66, 242, 000), resulting in 3 output classes. The "Other Attacks" class would be populated if additional CAPEC types were present.

### File Output Structure

All outputs written to: `injection-alert-system/data/processed/v3_907k_cleaned/`

```
v3_907k_cleaned/
├── audit_log.json              # Reproducibility metadata
├── cleaned_dataset.parquet     # Full cleaned dataset
├── train.parquet              # Training split (80%)
├── validation.parquet         # Validation split (10%)
├── test.parquet              # Test split (10%)
└── quarantine_dataset.parquet # Suspicious "Normal" samples
```

---

## Dataset Statistics

### Processing Summary

| Metric | Value |
|--------|-------|
| Original dataset size | 907,815 rows |
| Malformed rows removed | 2 rows |
| Exact duplicates removed | 544,760 rows |
| Suspicious benign quarantined | 35,298 rows |
| **Final dataset size** | **327,755 rows** |

### Class Distribution

| Class | Count | Percentage | Ratio |
|-------|-------|------------|-------|
| SQL Injection | 184,645 | 56.34% | 1.000 |
| Normal | 132,020 | 40.28% | 0.715 |
| Code Injection | 11,090 | 3.38% | 0.060 |
| **Total** | **327,755** | **100.00%** | - |

### Imbalance Analysis

```
Majority Class:  SQL Injection (184,645 samples)
Minority Class:  Code Injection (11,090 samples)
Imbalance Ratio: 16.65:1
Minority Representation: 3.38%
```

**Assessment:** SEVERE imbalance detected. Recommendations:
- Use class weights during training
- Consider focal loss for minority class handling
- Implement oversampling for Code Injection samples

### Stratified Split Distribution

| Split | Rows | Percentage |
|-------|------|------------|
| Train | 262,204 | 80.00% |
| Validation | 32,775 | 10.00% |
| Test | 32,776 | 10.00% |

**Stratification Verification:**
- SQL Injection: 56.34% in all splits
- Normal: 40.28% in all splits
- Code Injection: 3.38% in all splits

### Cross-Split Duplicate Check

| Check | Result |
|-------|--------|
| Train/Validation duplicates | 0 |
| Train/Test duplicates | 0 |
| Validation/Test duplicates | 0 |

**Status:** ✅ No data leakage between splits

---

## File Integrity Verification

### SHA256 Checksums

| File | SHA256 Hash | Size |
|------|-------------|------|
| train.parquet | `b6fd0af3fe84e12c9fbfab0b8ce6035340ac9564221a901d726bf9dac11f22ae` | 35,723,032 bytes |
| validation.parquet | `22d4e73fc781e0c4ae1f3df0ecef8d52eb9aed47523aa9ab4e24be6446994659` | 4,321,564 bytes |
| test.parquet | `eaf3e8156271da1066d65e876e0c145c2ec1884c7d5409d67f7c0c59773fd622` | 4,280,288 bytes |
| cleaned_dataset.parquet | `5f08c75c1607550184fd4b42a607d2d3de5e88db1fcfd8e017d8833a9557458c` | 31,522,874 bytes |
| quarantine_dataset.parquet | - | 4,261,265 bytes |
| audit_log.json | - | 3,049 bytes |

### Audit Log Structure

The `audit_log.json` contains:

```json
{
    "metadata": {
        "pipeline_version": "2.0.0",
        "random_seed": 42,
        "timestamp_utc": "2026-03-04T16:53:32.278021+00:00",
        "git_commit": "Unknown"
    },
    "counts": { /* Stage-by-stage row counts */ },
    "statistics": {
        "class_distribution_final": { /* Class counts */ },
        "near_duplicate_analysis": { /* MinHash results */ },
        "payload_length": { /* Length statistics */ },
        "estimated_tokens": { /* Token counts */ }
    },
    "files": { /* SHA256 checksums */ }
}
```

---

## Payload Statistics

### Character Length Distribution (Training Set)

| Metric | Value |
|--------|-------|
| Mean | 116.4 characters |
| Median | 100.0 characters |
| 95th percentile | 238.0 characters |
| 99th percentile | 357.0 characters |
| Maximum | 686 characters |

### Token Estimation (BPE Tokenizer, ~4 chars/token)

| Metric | Value |
|--------|-------|
| Mean | 29.1 tokens |
| 95th percentile | 59.5 tokens |
| 99th percentile | 89.2 tokens |
| Maximum | 171.5 tokens |

### MAX_LEN Recommendation

**Recommended:** 128 tokens

- 95% of payloads fit within 60 tokens
- 99% of payloads fit within 89 tokens
- MAX_LEN of 128 provides sufficient headroom

---

## Near-Duplicate Analysis

| Metric | Value |
|--------|-------|
| Sample size analyzed | 50,000 |
| Similarity threshold | 0.90 |
| Payloads above threshold | 39.47% |
| Estimated clusters | 10,903 |

**Assessment:** Moderate near-duplicate rate (39.5%) - may introduce bias in model training.

---

## Quarantine Analysis

### Statistics

| Metric | Value |
|--------|-------|
| Quarantined rows | 35,298 |
| Original benign class | 167,318 |
| Quarantine percentage | 21.10% of benign |

### Heuristics Applied

Suspicious patterns that triggered quarantine:
- `\b(select|union|sleep|benchmark)\b` - SQL keywords
- `1\s*=\s*1` - Boolean-based SQLi
- `<script>` - XSS patterns
- `\||&&|;` - Command injection
- `\.\./` - Path traversal

**Assessment:** Heuristics may be overly aggressive (21.1% of benign class quarantined).

---

## Technical Issues and Resolutions

### Issue 1: Unicode Encoding Error

**Description:** Console output failed when printing Unicode checkmark (✓) on Windows.

**Error Message:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' 
in position 2: character maps to <undefined>
```

**Root Cause:** Windows default console encoding (cp1252) cannot represent Unicode code point U+2713.

**Resolution:** Replaced `print("\n✓ PIPELINE EXECUTION COMPLETE.")` with `print("\n[OK] PIPELINE EXECUTION COMPLETE.")`

**Impact:** None - occurred after all data processing complete.

### Issue 2: Class Imbalance

**Description:** Severe imbalance between SQL Injection (56.34%) and Code Injection (3.38%).

**Resolution:** Documented in recommendations; requires training-time handling (class weights, focal loss).

---

## Recommendations

### For Model Training

1. **Class Weights:** Implement weighted loss to address 16.65:1 imbalance
2. **Focal Loss:** Consider for minority class (Code Injection) handling
3. **MAX_LEN:** Set to 128 based on payload analysis
4. **Monitoring:** Track overfitting on majority class (SQL Injection)
5. **Validation:** Test on held-out real-world traffic if available
6. **Augmentation:** Consider data augmentation for Code Injection samples

### For Cross-Platform Unicode Handling

1. **Console Output:** Use ASCII-only characters for status messages
2. **File I/O:** Always use UTF-8 encoding for text files
3. **Logging:** Implement platform-aware encoding detection
4. **Testing:** Validate pipeline on both Windows and Unix environments

### For Future Pipeline Runs

1. **Encoding:** Set console to UTF-8 mode (`chcp 65001` on Windows)
2. **Logging:** Redirect detailed logs to file instead of console
3. **Progress:** Use progress bars compatible with Windows console

---

## Conclusion

The SR-BH 2020 HTTP Attack Dataset cleaning pipeline executed successfully, producing a high-quality, deduplicated dataset of 327,755 unique HTTP payloads suitable for transformer-based WAF training. Despite the Unicode encoding error at the final output stage, all data processing completed successfully with full output integrity verified.

The dataset exhibits severe class imbalance (16.65:1) requiring specialized training techniques. The stratified splits maintain proper class distribution with no data leakage between partitions.

**Status:** ✅ **PIPELINE EXECUTION SUCCESSFUL**

---

## Appendix: Timestamp Information

| Event | Timestamp |
|-------|-----------|
| Pipeline Start | 2026-03-04T16:53:00+00:00 (estimated) |
| Audit Log Written | 2026-03-04T16:53:32.278021+00:00 |
| Audit Report Generated | 2026-03-04T16:58:00+00:00 |

---

## Appendix: File Locations

**Raw Data:**
```
G:\Documents\PDDDD\injection-alert-system\data\raw\data_capec_multilabel.csv
```

**Processed Output:**
```
G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned\
```

**Pipeline Script:**
```
G:\Documents\PDDDD\clean_907k.py
```

**Audit Script:**
```
G:\Documents\PDDDD\dataset_audit.py
```

---

*End of Audit Report*
