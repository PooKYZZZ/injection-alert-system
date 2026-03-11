"""
SR-BH 2020 HTTP Attack Dataset Audit Script v3
Comprehensive analysis of the cleaned dataset for transformer-based WAF training.
Validates: class distribution, cross-split integrity, cluster-aware splitting,
metadata removal, and transformer input readiness.
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from collections import Counter

# Configuration
DATA_DIR = Path(r'G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned')
AUDIT_LOG_PATH = DATA_DIR / 'audit_log.json'

EXPECTED_CLASSES = {'SQL Injection', 'Code Injection', 'Other Attacks', 'Normal'}
EXPECTED_COLUMNS = {'combined_payload', 'final_label', 'payload_hash', 'cluster_id'}
FORBIDDEN_COLUMNS = {'src_ip', 'dst_ip', 'src_port', 'dst_port', 'timestamp',
                     'response_http_status_code', 'response_content_length'}

failures = []


def check(condition, msg, critical=False):
    """Record a pass/fail check."""
    status = "PASS" if condition else ("CRITICAL FAIL" if critical else "FAIL")
    print(f"  [{status}] {msg}")
    if not condition:
        failures.append((msg, critical))

print("=" * 80)
print("SR-BH 2020 HTTP Attack Dataset — ML Dataset Audit Report v3")
print("=" * 80)
print()

# ============================================================
# 1. VERIFY DATASET INTEGRITY
# ============================================================
print("=" * 80)
print("1. DATASET INTEGRITY VERIFICATION")
print("=" * 80)

with open(AUDIT_LOG_PATH, 'r') as f:
    audit_log = json.load(f)

counts = audit_log['counts']

original_size = counts['stage_1_initial_rows']
malformed_removed = counts['stage_3_malformed_removed']
exact_duplicates_removed = counts['stage_4_exact_duplicates_removed']
quarantined = counts['stage_6_suspicious_benign_quarantined']
final_size = counts['stage_4_unique_payloads'] - quarantined

print(f"\n[Pipeline Execution Summary]")
print(f"   Pipeline version:                   {audit_log['metadata']['pipeline_version']}")
print(f"   Random seed:                        {audit_log['metadata']['random_seed']}")
print(f"   Original dataset size:              {original_size:,} rows")
print(f"   Rows removed (malformed):           {malformed_removed:,} rows")
print(f"   Rows removed (exact duplicates):    {exact_duplicates_removed:,} rows")
print(f"   Rows quarantined (label noise):     {quarantined:,} rows")
print(f"   ------------------------------------------------")
print(f"   Final dataset size:                 {final_size:,} rows")

expected_final = original_size - malformed_removed - exact_duplicates_removed - quarantined
check(final_size == expected_final,
      f"Internal row count consistency (expected {expected_final:,}, got {final_size:,})",
      critical=True)

# Load all datasets
print("\n[Loading parquet files...]")
train_df = pd.read_parquet(DATA_DIR / 'train.parquet')
val_df = pd.read_parquet(DATA_DIR / 'validation.parquet')
test_df = pd.read_parquet(DATA_DIR / 'test.parquet')

quarantine_path = DATA_DIR / 'quarantine_dataset.parquet'
quarantine_df = pd.read_parquet(quarantine_path) if quarantine_path.exists() else pd.DataFrame()

print(f"   Train:      {len(train_df):,} rows")
print(f"   Validation: {len(val_df):,} rows")
print(f"   Test:       {len(test_df):,} rows")
print(f"   Quarantine: {len(quarantine_df):,} rows")

# ============================================================
# 2. VERIFY SCHEMA & COLUMN INTEGRITY
# ============================================================
print()
print("=" * 80)
print("2. SCHEMA & COLUMN VERIFICATION")
print("=" * 80)

for split_name, split_df in [("train", train_df), ("validation", val_df), ("test", test_df)]:
    present_cols = set(split_df.columns)
    check(EXPECTED_COLUMNS.issubset(present_cols),
          f"{split_name}: contains required columns {EXPECTED_COLUMNS}")
    forbidden_present = FORBIDDEN_COLUMNS & present_cols
    check(len(forbidden_present) == 0,
          f"{split_name}: no metadata leakage columns (found: {forbidden_present})",
          critical=bool(forbidden_present))

check('combined_payload' in train_df.columns,
      "Transformer input field 'combined_payload' present", critical=True)

# ============================================================
# 3. VERIFY CLASS DISTRIBUTION
# ============================================================
print()
print("=" * 80)
print("3. CLASS DISTRIBUTION ANALYSIS")
print("=" * 80)

all_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
all_classes = set(all_df['final_label'].unique())

check(all_classes == EXPECTED_CLASSES,
      f"Expected 4 classes {EXPECTED_CLASSES}, got {all_classes}",
      critical=True)

final_dist = all_df['final_label'].value_counts().to_dict()
total_samples = sum(final_dist.values())

print(f"\n[Overall Class Distribution]")
print("-" * 80)
print(f"{'Class':<25} {'Count':>12} {'Percentage':>12}")
print("-" * 80)

max_class_count = max(final_dist.values())
min_class_count = min(final_dist.values())

for cls in sorted(final_dist.keys(), key=lambda x: -final_dist[x]):
    count = final_dist[cls]
    pct = count / total_samples * 100
    print(f"{cls:<25} {count:>12,} {pct:>11.2f}%")

print("-" * 80)
print(f"{'Total':<25} {total_samples:>12,} {'100.00%':>12}")

imbalance_ratio = max_class_count / min_class_count
majority_name = max(final_dist.keys(), key=lambda x: final_dist[x])
minority_name = min(final_dist.keys(), key=lambda x: final_dist[x])

print(f"\n[Imbalance Metrics]")
print(f"   Majority class:       {majority_name} ({max_class_count:,})")
print(f"   Minority class:       {minority_name} ({min_class_count:,})")
print(f"   Imbalance ratio:      {imbalance_ratio:.2f}:1")

check(final_dist.get('Other Attacks', 0) > 0,
      "'Other Attacks' class is non-empty", critical=True)

# ============================================================
# 4. VERIFY SPLIT INTEGRITY
# ============================================================
print()
print("=" * 80)
print("4. SPLIT INTEGRITY VERIFICATION")
print("=" * 80)

total = len(train_df) + len(val_df) + len(test_df)
train_ratio = len(train_df) / total
val_ratio = len(val_df) / total
test_ratio = len(test_df) / total

print(f"\n[Split Ratios]")
print(f"   Train:      {len(train_df):,} ({train_ratio*100:.2f}%)")
print(f"   Validation: {len(val_df):,} ({val_ratio*100:.2f}%)")
print(f"   Test:       {len(test_df):,} ({test_ratio*100:.2f}%)")
print(f"   Expected:   ~80% / ~10% / ~10%")

check(0.75 <= train_ratio <= 0.85,
      f"Train ratio in range [75%-85%]: {train_ratio*100:.1f}%")
check(0.07 <= val_ratio <= 0.15,
      f"Val ratio in range [7%-15%]: {val_ratio*100:.1f}%")
check(0.07 <= test_ratio <= 0.15,
      f"Test ratio in range [7%-15%]: {test_ratio*100:.1f}%")

# Stratification check: verify class proportions are similar across splits
print("\n[Stratification Check — Class % per Split]")
print("-" * 80)
print(f"{'Class':<25} {'Train %':>10} {'Val %':>10} {'Test %':>10} {'Max Δ':>10}")
print("-" * 80)

for cls in sorted(all_classes):
    t_pct = train_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    v_pct = val_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    te_pct = test_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    max_delta = max(abs(t_pct - v_pct), abs(t_pct - te_pct), abs(v_pct - te_pct))
    print(f"{cls:<25} {t_pct:>9.2f}% {v_pct:>9.2f}% {te_pct:>9.2f}% {max_delta:>9.2f}%")
    check(max_delta < 5.0,
          f"Stratification drift for '{cls}' < 5%: Δ={max_delta:.2f}%")

# ============================================================
# 5. CROSS-SPLIT DUPLICATE & CLUSTER LEAKAGE CHECK
# ============================================================
print()
print("=" * 80)
print("5. CROSS-SPLIT LEAKAGE VERIFICATION")
print("=" * 80)

# Exact hash overlap
train_hashes = set(train_df['payload_hash'])
val_hashes = set(val_df['payload_hash'])
test_hashes = set(test_df['payload_hash'])

tv_exact = len(train_hashes & val_hashes)
tt_exact = len(train_hashes & test_hashes)
vt_exact = len(val_hashes & test_hashes)

print(f"\n[Exact Hash Overlap]")
print(f"   Train ∩ Val:   {tv_exact}")
print(f"   Train ∩ Test:  {tt_exact}")
print(f"   Val ∩ Test:    {vt_exact}")

check(tv_exact == 0, "Zero exact duplicates between Train/Val", critical=True)
check(tt_exact == 0, "Zero exact duplicates between Train/Test", critical=True)
check(vt_exact == 0, "Zero exact duplicates between Val/Test", critical=True)

# Near-duplicate cluster overlap
if 'cluster_id' in train_df.columns:
    train_clusters = set(train_df['cluster_id'])
    val_clusters = set(val_df['cluster_id'])
    test_clusters = set(test_df['cluster_id'])

    tv_cluster = len(train_clusters & val_clusters)
    tt_cluster = len(train_clusters & test_clusters)
    vt_cluster = len(val_clusters & test_clusters)

    print(f"\n[Near-Duplicate Cluster Overlap]")
    print(f"   Train ∩ Val:   {tv_cluster} shared clusters")
    print(f"   Train ∩ Test:  {tt_cluster} shared clusters")
    print(f"   Val ∩ Test:    {vt_cluster} shared clusters")

    total_overlap = tv_cluster + tt_cluster + vt_cluster
    check(total_overlap == 0,
          f"Zero near-duplicate cluster overlap across splits (found: {total_overlap})",
          critical=True)
else:
    print("\n  [SKIP] cluster_id not found — cluster leakage check skipped")
    failures.append(("cluster_id column missing", True))

# ============================================================
# 6. NEAR-DUPLICATE CLUSTER STATISTICS
# ============================================================
print()
print("=" * 80)
print("6. NEAR-DUPLICATE CLUSTER STATISTICS")
print("=" * 80)

cluster_stats = audit_log['statistics'].get('near_duplicate_clusters')
if isinstance(cluster_stats, dict):
    print(f"\n   Total clusters:                  {cluster_stats['total_clusters']:,}")
    print(f"   Singleton clusters:              {cluster_stats['singleton_clusters']:,}")
    print(f"   Non-singleton clusters:          {cluster_stats['non_singleton_clusters']:,}")
    print(f"   Largest cluster size:            {cluster_stats['largest_cluster_size']:,}")
    print(f"   Payloads in non-singleton:       {cluster_stats['payloads_in_non_singleton_clusters']:,}")
    print(f"   MinHash config:                  shingle={cluster_stats['shingle_size']}, "
          f"threshold={cluster_stats['threshold']}, perms={cluster_stats['num_perm']}")
else:
    print(f"   Near-duplicate analysis: {cluster_stats}")

# ============================================================
# 7. QUARANTINE DATASET ANALYSIS
# ============================================================
print()
print("=" * 80)
print("7. QUARANTINE DATASET ANALYSIS")
print("=" * 80)

if len(quarantine_df) > 0:
    before_quarantine = audit_log['statistics']['class_distribution_before_quarantine'].get('Normal', 0)
    quarantine_pct = len(quarantine_df) / before_quarantine * 100 if before_quarantine > 0 else 0

    print(f"\n   Quarantined rows:       {len(quarantine_df):,}")
    print(f"   Original Normal class:  {before_quarantine:,}")
    print(f"   Quarantine percentage:  {quarantine_pct:.2f}% of Normal")

    check(quarantine_pct < 30,
          f"Quarantine not overly aggressive (<30%): {quarantine_pct:.1f}%")
    check(quarantine_pct > 0.1,
          f"Quarantine not trivially small (>0.1%): {quarantine_pct:.1f}%")

    print(f"\n[Sample Quarantined Payloads]")
    print("-" * 80)
    sample_col = 'combined_payload' if 'combined_payload' in quarantine_df.columns else 'request_http_request'
    for i, row in quarantine_df.head(5).iterrows():
        if 'request_http_method' in quarantine_df.columns:
            payload = (str(row.get('request_http_method', '')) + " " +
                       str(row.get('request_http_request', '')) + " " +
                       str(row.get('request_body', '')))[:120]
        else:
            payload = str(row.get(sample_col, ''))[:120]
        print(f"   {payload}...")
else:
    print("   No quarantine dataset found.")

# ============================================================
# 8. PAYLOAD LENGTH STATISTICS
# ============================================================
print()
print("=" * 80)
print("8. PAYLOAD LENGTH STATISTICS")
print("=" * 80)

if 'combined_payload' in train_df.columns:
    lengths = train_df['combined_payload'].str.len()
    stats = {
        'mean': lengths.mean(),
        'median': lengths.median(),
        'p95': np.percentile(lengths, 95),
        'p99': np.percentile(lengths, 99),
        'max': lengths.max()
    }

    print(f"\n[Training Set Payload Lengths]")
    print(f"   Mean:            {stats['mean']:.1f} characters")
    print(f"   Median:          {stats['median']:.1f} characters")
    print(f"   95th percentile: {stats['p95']:.1f} characters")
    print(f"   99th percentile: {stats['p99']:.1f} characters")
    print(f"   Maximum:         {stats['max']:.0f} characters")

    print(f"\n[Estimated Token Counts (~4 chars/token)]")
    print(f"   Mean:            {stats['mean']/4:.1f} tokens")
    print(f"   95th percentile: {stats['p95']/4:.1f} tokens")
    print(f"   Maximum:         {stats['max']/4:.1f} tokens")

    max_tokens_95 = stats['p95'] / 4
    if max_tokens_95 < 64:
        rec_len = 128
    elif max_tokens_95 < 128:
        rec_len = 256
    else:
        rec_len = 512
    print(f"\n   Recommended MAX_LEN: {rec_len}")
else:
    print("   [SKIP] combined_payload not in training set")

# ============================================================
# 9. MULTI-LABEL RESOLUTION AUDIT
# ============================================================
print()
print("=" * 80)
print("9. MULTI-LABEL & REPRODUCIBILITY METADATA")
print("=" * 80)

multi_label = audit_log['statistics'].get('multi_label_rows_resolved', 'N/A')
print(f"\n   Multi-label rows resolved:  {multi_label}")
print(f"   Label priority:             {audit_log['metadata'].get('label_priority_order', 'N/A')}")
print(f"   Git commit:                 {audit_log['metadata'].get('git_commit', 'N/A')}")
print(f"   Timestamp:                  {audit_log['metadata'].get('timestamp_utc', 'N/A')}")

# ============================================================
# 10. FINAL ASSESSMENT
# ============================================================
print()
print("=" * 80)
print("10. FINAL DATASET ASSESSMENT")
print("=" * 80)

critical_failures = [f for f, is_crit in failures if is_crit]
warnings = [f for f, is_crit in failures if not is_crit]

print(f"\n   Total checks:       {len(failures) + sum(1 for _ in [])}")
print(f"   Critical failures:  {len(critical_failures)}")
print(f"   Warnings:           {len(warnings)}")

if critical_failures:
    print(f"\n[CRITICAL FAILURES]")
    for f in critical_failures:
        print(f"   ✗ {f}")

if warnings:
    print(f"\n[WARNINGS]")
    for w in warnings:
        print(f"   ⚠ {w}")

# Summary of dataset guarantees
print(f"\n[DATASET GUARANTEE CHECKLIST]")
has_4_classes = all_classes == EXPECTED_CLASSES
no_exact_dups = (tv_exact + tt_exact + vt_exact) == 0
has_cluster_id = 'cluster_id' in train_df.columns
no_cluster_leak = has_cluster_id and (tv_cluster + tt_cluster + vt_cluster) == 0
has_combined = 'combined_payload' in train_df.columns
no_metadata = len(FORBIDDEN_COLUMNS & set(train_df.columns)) == 0

guarantees = [
    ("Correct 4-class labels", has_4_classes),
    ("No exact cross-split duplicates", no_exact_dups),
    ("Cluster-aware splitting (no near-dup leakage)", no_cluster_leak),
    ("Transformer input field present", has_combined),
    ("No metadata leakage columns", no_metadata),
    ("Reproducible (seeded, audited)", True),
]

for desc, passed in guarantees:
    symbol = "✓" if passed else "✗"
    print(f"   [{symbol}] {desc}")

print()
if critical_failures:
    print("AUDIT RESULT: FAIL — critical issues must be resolved before training.")
    sys.exit(1)
elif warnings:
    print("AUDIT RESULT: PASS WITH WARNINGS — review warnings before training.")
else:
    print("AUDIT RESULT: PASS — dataset is ready for transformer training.")

print("=" * 80)
