"""
Dataset Diagnostic Script — Pre-Pipeline-Refinement Analysis
=============================================================
Runs the 6 diagnostic steps from the best-practice implementation plan:

1. Inspect the largest cluster and confirm its origin
2. Analyze cluster size distribution
3. Verify the stratified group split behavior
4. Re-evaluate MinHash similarity parameters (threshold sweep)
5. Review quarantine rules using sampled rows
6. Summarize findings and recommended actions

Reads from the ALREADY-PRODUCED pipeline artifacts + raw data.
Does NOT modify any files.
"""

import pandas as pd
import numpy as np
import hashlib
import json
import re
import urllib.parse
import html
import unicodedata
from pathlib import Path
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────
DATA_DIR = Path(r'G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned')
RAW_PATH = Path(r'G:\Documents\PDDDD\injection-alert-system\data\raw\data_capec_multilabel.csv')
AUDIT_LOG = DATA_DIR / 'audit_log.json'

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

SEP = "=" * 80

# ── Helpers ────────────────────────────────────────────────────
def canonicalize_text(text):
    if not isinstance(text, str):
        return ""
    text = urllib.parse.unquote(text)
    text = html.unescape(text)
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\x00', '')
    text = ' '.join(text.split()).lower()
    return text

# Current quarantine regex from clean_907k.py
SUSPICIOUS_PATTERNS = [
    r'\b(select|union|insert|update|delete|drop|exec|xp_)\b',
    r'\b(sleep|benchmark|waitfor)\b',
    r'1\s*=\s*1',
    r'(--|#)\s*$',
    r'<script',
    r'<img\b',
    r'\bonerror\b',
    r'javascript\s*:',
    r'[|;&]',
    r'&&',
    r'\$\(',
    r'\.\.[/\\]',
    r'%2e%2e',
    r'\{\{',
]
SUSPICIOUS_REGEX = re.compile('|'.join(SUSPICIOUS_PATTERNS), re.IGNORECASE)

# ── Load artifacts ─────────────────────────────────────────────
print(SEP)
print("DATASET DIAGNOSTIC REPORT")
print(SEP)

print("\n[Loading artifacts...]")
full_df = pd.read_parquet(DATA_DIR / 'cleaned_dataset.parquet')
train_df = pd.read_parquet(DATA_DIR / 'train.parquet')
val_df = pd.read_parquet(DATA_DIR / 'validation.parquet')
test_df = pd.read_parquet(DATA_DIR / 'test.parquet')
quarantine_df = pd.read_parquet(DATA_DIR / 'quarantine_dataset.parquet')

with open(AUDIT_LOG, 'r') as f:
    audit = json.load(f)

total = len(full_df)
print(f"   Full cleaned: {total:,}")
print(f"   Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
print(f"   Quarantine: {len(quarantine_df):,}")

# ================================================================
# DIAGNOSTIC 1: Inspect the Largest Cluster
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC 1: LARGEST CLUSTER INSPECTION")
print(SEP)

cluster_sizes = full_df['cluster_id'].value_counts()
largest_cid = cluster_sizes.index[0]
largest_size = cluster_sizes.iloc[0]
print(f"\nLargest cluster ID:  {largest_cid}")
print(f"Largest cluster size: {largest_size:,} ({largest_size/total*100:.1f}% of dataset)")

largest_cluster = full_df[full_df['cluster_id'] == largest_cid]

# Class distribution within this cluster
lc_class_dist = largest_cluster['final_label'].value_counts()
print(f"\nClass distribution within largest cluster:")
for cls, cnt in lc_class_dist.items():
    print(f"   {cls}: {cnt:,} ({cnt/largest_size*100:.1f}%)")

# Which split did this cluster land in?
for name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
    n_in_split = split_df[split_df['cluster_id'] == largest_cid].shape[0]
    if n_in_split > 0:
        print(f"\nLargest cluster landed entirely in: {name} ({n_in_split:,} rows)")

# Sample 20 payloads from the cluster
print(f"\n--- Sample payloads from largest cluster (20 random) ---")
sample = largest_cluster.sample(n=min(20, len(largest_cluster)), random_state=RANDOM_SEED)
for i, (_, row) in enumerate(sample.iterrows()):
    payload = row['combined_payload']
    trunc = payload[:150] + "..." if len(payload) > 150 else payload
    print(f"  [{i+1:2d}] [{row['final_label']:16s}] {trunc}")

# Payload length stats for this cluster
lc_lengths = largest_cluster['combined_payload'].str.len()
print(f"\nPayload length stats (largest cluster):")
print(f"   Mean:   {lc_lengths.mean():.1f}")
print(f"   Median: {lc_lengths.median():.1f}")
print(f"   Min:    {lc_lengths.min()}")
print(f"   Max:    {lc_lengths.max()}")
print(f"   Std:    {lc_lengths.std():.1f}")

# Unique method distribution
method_dist = largest_cluster['request_http_method'].value_counts()
print(f"\nHTTP methods in largest cluster:")
for m, c in method_dist.items():
    print(f"   {m}: {c:,}")

# Check how many unique body prefixes exist (first 30 chars)
body_prefixes = largest_cluster['combined_payload'].str[:50].value_counts()
print(f"\nUnique 50-char prefixes: {len(body_prefixes):,} (out of {largest_size:,} payloads)")
print(f"Top-5 prefixes:")
for prefix, cnt in body_prefixes.head(5).items():
    print(f"   [{cnt:5d}x] {prefix}")

# ================================================================
# DIAGNOSTIC 2: Cluster Size Distribution Analysis
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC 2: CLUSTER SIZE DISTRIBUTION")
print(SEP)

n_clusters = len(cluster_sizes)
n_singletons = int((cluster_sizes == 1).sum())
pct_singleton = n_singletons / n_clusters * 100

print(f"\nTotal clusters: {n_clusters:,}")
print(f"Singleton clusters: {n_singletons:,} ({pct_singleton:.1f}%)")
print(f"Non-singleton clusters: {n_clusters - n_singletons:,}")

# Size distribution buckets
buckets = [1, 2, 5, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, np.inf]
bucket_labels = []
for i in range(len(buckets) - 1):
    lo = int(buckets[i])
    hi = int(buckets[i + 1]) if buckets[i + 1] != np.inf else "∞"
    bucket_labels.append(f"{lo}-{hi}")

print(f"\nCluster size distribution:")
print(f"  {'Size Range':>15s} | {'Clusters':>10s} | {'Total Rows':>12s} | {'% of Dataset':>12s}")
print(f"  {'-'*15}-+-{'-'*10}-+-{'-'*12}-+-{'-'*12}")
for i in range(len(buckets) - 1):
    lo, hi = buckets[i], buckets[i + 1]
    mask = (cluster_sizes >= lo) & (cluster_sizes < hi)
    n = int(mask.sum())
    rows = int(cluster_sizes[mask].sum())
    pct = rows / total * 100
    print(f"  {bucket_labels[i]:>15s} | {n:>10,d} | {rows:>12,d} | {pct:>11.1f}%")

# Top-20 cluster sizes
print(f"\nTop-20 cluster sizes:")
for rank, (cid, size) in enumerate(cluster_sizes.head(20).items(), 1):
    cls_in = full_df[full_df['cluster_id'] == cid]['final_label'].value_counts()
    dominant_cls = cls_in.index[0]
    print(f"  #{rank:2d}: {size:>7,d} rows (dominant class: {dominant_cls})")

# Dataset fraction in top-N clusters
for n in [1, 5, 10, 20, 39]:
    top_n = cluster_sizes.head(n).sum()
    print(f"\nTop-{n} clusters encompass: {top_n:,} rows ({top_n/total*100:.1f}% of dataset)")

# 5-10% rule check
five_pct = total * 0.05
ten_pct = total * 0.10
clusters_above_5pct = (cluster_sizes > five_pct).sum()
clusters_above_10pct = (cluster_sizes > ten_pct).sum()
print(f"\nClusters exceeding 5% of dataset ({five_pct:,.0f}): {clusters_above_5pct}")
print(f"Clusters exceeding 10% of dataset ({ten_pct:,.0f}): {clusters_above_10pct}")

# ================================================================
# DIAGNOSTIC 3: Verify Stratified Group Split Behavior
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC 3: STRATIFIED GROUP SPLIT VERIFICATION")
print(SEP)

print(f"\nCurrent split sizes:")
print(f"   Train: {len(train_df):>8,d} ({len(train_df)/total*100:.1f}%)")
print(f"   Val:   {len(val_df):>8,d} ({len(val_df)/total*100:.1f}%)")
print(f"   Test:  {len(test_df):>8,d} ({len(test_df)/total*100:.1f}%)")

global_dist = full_df['final_label'].value_counts(normalize=True)
print(f"\nClass distribution comparison (% per split):")
print(f"  {'Class':>18s} | {'Global':>8s} | {'Train':>8s} | {'Val':>8s} | {'Test':>8s}")
print(f"  {'-'*18}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")

for cls in global_dist.index:
    g = global_dist[cls] * 100
    tr = train_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    vl = val_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    te = test_df['final_label'].value_counts(normalize=True).get(cls, 0) * 100
    print(f"  {cls:>18s} | {g:>7.1f}% | {tr:>7.1f}% | {vl:>7.1f}% | {te:>7.1f}%")

# Show which clusters dominate each split
print(f"\nCluster concentration per split:")
for name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
    sc = split_df['cluster_id'].value_counts()
    top_cid = sc.index[0] if len(sc) > 0 else None
    top_size = sc.iloc[0] if len(sc) > 0 else 0
    n_clusters_in = len(sc)
    print(f"   {name}: {n_clusters_in:,} clusters, largest={top_size:,} "
          f"({top_size/len(split_df)*100:.1f}% of split)")

# Test multiple StratifiedGroupKFold seeds to find better splits
print(f"\nCandidate split search (testing 20 random seeds)...")
from sklearn.model_selection import StratifiedGroupKFold

df_sorted = full_df.sort_values('payload_hash').reset_index(drop=True)
groups = df_sorted['cluster_id'].values
labels = df_sorted['final_label'].values

best_seed = None
best_score = float('inf')
results = []

for seed in range(50):
    try:
        sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        train_idx, temp_idx = next(sgkf.split(df_sorted, labels, groups))

        t_df = df_sorted.iloc[temp_idx]
        temp_groups = t_df['cluster_id'].values
        temp_labels = t_df['final_label'].values

        sgkf2 = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=seed)
        v_idx, te_idx = next(sgkf2.split(t_df, temp_labels, temp_groups))

        tr_n = len(train_idx)
        vl_n = len(v_idx)
        te_n = len(te_idx)

        tr_pct = tr_n / total * 100
        vl_pct = vl_n / total * 100
        te_pct = te_n / total * 100

        # Score: distance from ideal 80/10/10
        score = abs(tr_pct - 80) + abs(vl_pct - 10) + abs(te_pct - 10)

        # Also check class distribution drift
        tr_dist = df_sorted.iloc[train_idx]['final_label'].value_counts(normalize=True)
        max_drift = max(abs(tr_dist.get(c, 0) - global_dist[c]) * 100 for c in global_dist.index)
        score += max_drift * 2  # Penalize drift heavily

        results.append((seed, tr_pct, vl_pct, te_pct, max_drift, score))
        if score < best_score:
            best_score = score
            best_seed = seed
    except Exception as e:
        results.append((seed, 0, 0, 0, 99, 999))

print(f"\n  {'Seed':>4s} | {'Train%':>7s} | {'Val%':>7s} | {'Test%':>7s} | {'MaxDrift':>8s} | {'Score':>7s}")
print(f"  {'-'*4}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*8}-+-{'-'*7}")
# Show top-10 by score
results.sort(key=lambda x: x[5])
for seed, tr, vl, te, drift, sc in results[:10]:
    marker = " <-- BEST" if seed == best_seed else ""
    print(f"  {seed:>4d} | {tr:>6.1f}% | {vl:>6.1f}% | {te:>6.1f}% | {drift:>7.2f}% | {sc:>7.2f}{marker}")

print(f"\n  FINDING: The 100k cluster forces StratifiedGroupKFold into degenerate splits")
print(f"  because one indivisible group ≈ {largest_size/total*100:.0f}% of the data.")

# ================================================================
# DIAGNOSTIC 4: MinHash Threshold Sensitivity Analysis
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC 4: MinHash THRESHOLD SENSITIVITY (sampled)")
print(SEP)

try:
    from datasketch import MinHash, MinHashLSH

    # Use a representative sample (20k) for threshold sweep
    SAMPLE_N = 20000
    SHINGLE_SIZE = 5
    NUM_PERM = 128

    print(f"\nSampling {SAMPLE_N:,} payloads for threshold sweep...")

    # Load raw-ish data: we need identity_string, so reconstruct from cleaned
    sample_df = full_df.sample(n=min(SAMPLE_N, len(full_df)), random_state=RANDOM_SEED).copy()
    texts = sample_df['combined_payload'].tolist()
    indices = list(range(len(texts)))

    print(f"Building MinHash signatures...")
    minhashes = {}
    for i, text in enumerate(texts):
        m = MinHash(num_perm=NUM_PERM)
        shingles = [text[j:j + SHINGLE_SIZE].encode('utf8')
                    for j in range(max(1, len(text) - SHINGLE_SIZE + 1))]
        if shingles:
            m.update_batch(shingles)
        else:
            m.update(text.encode('utf8'))
        minhashes[i] = m

    print(f"Testing thresholds: 0.70, 0.75, 0.80, 0.85, 0.90, 0.95")

    class UnionFind:
        def __init__(self):
            self.parent = {}
            self.rank = {}
        def find(self, x):
            if x not in self.parent:
                self.parent[x] = x
                self.rank[x] = 0
            while self.parent[x] != x:
                self.parent[x] = self.parent[self.parent[x]]
                x = self.parent[x]
            return x
        def union(self, a, b):
            ra, rb = self.find(a), self.find(b)
            if ra == rb: return
            if self.rank[ra] < self.rank[rb]: ra, rb = rb, ra
            self.parent[rb] = ra
            if self.rank[ra] == self.rank[rb]: self.rank[ra] += 1

    for threshold in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
        for i, m in minhashes.items():
            try:
                lsh.insert(str(i), m)
            except ValueError:
                pass

        uf = UnionFind()
        for i in minhashes:
            for other in lsh.query(minhashes[i]):
                oi = int(other)
                if oi != i:
                    uf.union(i, oi)

        cluster_map = {}
        for i in minhashes:
            cluster_map[i] = uf.find(i)

        sizes = Counter(cluster_map.values())
        size_vals = sorted(sizes.values(), reverse=True)
        n_clusters = len(sizes)
        n_sing = sum(1 for s in size_vals if s == 1)
        largest = size_vals[0] if size_vals else 0
        top5 = size_vals[:5]
        above_1k = sum(1 for s in size_vals if s > SAMPLE_N * 0.05)

        print(f"\n  threshold={threshold:.2f}: {n_clusters:,} clusters, "
              f"{n_sing:,} singletons, largest={largest:,}, "
              f"top-5={top5}, >5%_of_sample={above_1k}")

except ImportError:
    print("  SKIPPED: datasketch not installed")

# ================================================================
# DIAGNOSTIC 5: Quarantine Rule Review
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC 5: QUARANTINE RULE REVIEW")
print(SEP)

# Quarantine statistics
quarantine_count = len(quarantine_df)
normal_before_quarantine = audit['statistics']['class_distribution_before_quarantine']['Normal']
quarantine_rate = quarantine_count / normal_before_quarantine * 100

print(f"\nNormal rows before quarantine: {normal_before_quarantine:,}")
print(f"Quarantined rows: {quarantine_count:,}")
print(f"Quarantine rate: {quarantine_rate:.1f}%")

# Sample 200 quarantined rows and categorize them
sample_n = min(300, len(quarantine_df))
q_sample = quarantine_df.sample(n=sample_n, random_state=RANDOM_SEED)

# Analyze which pattern triggered each quarantine
individual_patterns = {
    'SQL keywords (select/union/insert/update/delete/drop/exec)':
        re.compile(r'\b(select|union|insert|update|delete|drop|exec|xp_)\b', re.I),
    'SQL functions (sleep/benchmark/waitfor)':
        re.compile(r'\b(sleep|benchmark|waitfor)\b', re.I),
    'Tautology (1=1)':
        re.compile(r'1\s*=\s*1', re.I),
    'SQL comment ending (-- / #)':
        re.compile(r'(--|#)\s*$', re.I),
    'XSS <script>':
        re.compile(r'<script', re.I),
    'XSS <img>':
        re.compile(r'<img\b', re.I),
    'XSS onerror':
        re.compile(r'\bonerror\b', re.I),
    'XSS javascript:':
        re.compile(r'javascript\s*:', re.I),
    'Shell metachar (| ; &)':
        re.compile(r'[|;&]', re.I),
    'Shell &&':
        re.compile(r'&&', re.I),
    'Subshell $(':
        re.compile(r'\$\(', re.I),
    'Path traversal (../)':
        re.compile(r'\.\.[/\\]', re.I),
    'Encoded traversal (%2e%2e)':
        re.compile(r'%2e%2e', re.I),
    'Template injection {{':
        re.compile(r'\{\{', re.I),
}

# Count which patterns fire on the quarantine sample
# Build combined_payload for quarantine rows (not exported by pipeline)
q_sample = q_sample.copy()
q_sample['combined_payload'] = (
    q_sample['canonical_method'].fillna('') + " " +
    q_sample['canonical_path'].fillna('') + " " +
    q_sample['canonical_body'].fillna('')
)

print(f"\nPattern trigger frequency on {sample_n} sampled quarantined rows:")
trigger_counts = {}
for name, pat in individual_patterns.items():
    n_matches = q_sample['combined_payload'].str.contains(pat, regex=True).sum()
    trigger_counts[name] = n_matches
    pct = n_matches / sample_n * 100
    flag = " <<<" if pct > 50 else ""
    print(f"  {name:50s}: {n_matches:>4d} ({pct:>5.1f}%){flag}")

# Identify the DOMINANT trigger: which single pattern causes the most quarantines?
# Check: how many rows are ONLY caught by the shell metachar rule?
shell_meta = re.compile(r'[|;&]', re.I)
no_other_match = 0
shell_only_samples = []
for _, row in q_sample.iterrows():
    payload = row['combined_payload']
    if shell_meta.search(payload):
        other_hit = False
        for name, pat in individual_patterns.items():
            if name == 'Shell metachar (| ; &)' or name == 'Shell &&':
                continue
            if pat.search(payload):
                other_hit = True
                break
        if not other_hit:
            no_other_match += 1
            if len(shell_only_samples) < 10:
                shell_only_samples.append(payload[:200])

print(f"\nRows caught ONLY by shell metachar [|;&] (no other pattern): "
      f"{no_other_match}/{sample_n} ({no_other_match/sample_n*100:.1f}%)")

if shell_only_samples:
    print(f"\nSample payloads caught ONLY by [|;&]:")
    for i, p in enumerate(shell_only_samples[:10]):
        print(f"  [{i+1}] {p[:150]}...")

# Analyze the specific characters triggering [|;&]
ampersand_only = 0
pipe_only = 0
semicolon_only = 0
for _, row in q_sample.iterrows():
    payload = row['combined_payload']
    has_amp = '&' in payload
    has_pipe = '|' in payload
    has_semi = ';' in payload
    if has_amp and not has_pipe and not has_semi:
        ampersand_only += 1

print(f"\nIn quarantine sample — rows containing ONLY '&' (no | or ;): "
      f"{ampersand_only}/{sample_n} ({ampersand_only/sample_n*100:.1f}%)")
print(f"  → '&' in URLs/form data is normal HTTP traffic, not shell injection")

# Estimate true positive rate (heuristic: check if payload has SQLi/XSS attack structure)
real_attack_patterns = re.compile(
    r'(\bunion\b.*\bselect\b|'        # UNION SELECT
    r'\bor\b\s+\d+\s*=\s*\d+|'        # OR 1=1
    r'<script[^>]*>|'                  # Full <script> tag
    r'\bonerror\s*=|'                  # Event handler
    r';\s*(ls|cat|wget|curl|rm)\b|'    # Shell command after ;
    r'\|\s*(ls|cat|wget|curl|rm)\b)',   # Shell command after |
    re.I
)
likely_attacks = q_sample['combined_payload'].str.contains(real_attack_patterns, regex=True).sum()
print(f"\nEstimated true positives (structured attack patterns): "
      f"{likely_attacks}/{sample_n} ({likely_attacks/sample_n*100:.1f}%)")
print(f"Estimated false positive rate: {(sample_n - likely_attacks)/sample_n*100:.1f}%")

# ================================================================
# DIAGNOSTIC 6: Summary and Recommended Actions
# ================================================================
print(f"\n{SEP}")
print("DIAGNOSTIC SUMMARY & RECOMMENDED ACTIONS")
print(SEP)

print("""
FINDING 1 — LARGEST CLUSTER ANALYSIS
  The largest cluster ({largest_size:,} rows, {pct_of_data:.1f}% of dataset) must be
  characterized. See sampled payloads above for origin assessment.
  → If scanner noise: cap cluster size during preprocessing
  → If overly aggressive LSH: raise threshold to 0.85-0.90

FINDING 2 — CLUSTER SIZE DISTRIBUTION
  {n_above_5pct} cluster(s) exceed 5% of the dataset.
  {n_above_1k} clusters exceed 1,000 members.
  The top-10 clusters account for a large fraction of data.
  → Cluster capping at MAX_CLUSTER_SIZE is recommended.

FINDING 3 — SPLIT DEGRADATION
  Current splits are {tr_pct:.1f}/{vl_pct:.1f}/{te_pct:.1f} (target: 80/10/10).
  Validation set has only {val_n:,} rows — unusable for evaluation.
  → Root cause: the 100k cluster is indivisible under GroupKFold.
  → Fix: cap large clusters before splitting.

FINDING 4 — QUARANTINE OVER-AGGRESSIVENESS
  Quarantine rate: {q_rate:.1f}% of Normal class.
  Primary false-positive trigger: [|;&] regex matches '&' in URLs/forms.
  → Fix: replace [|;&] with context-sensitive patterns that require
    shell command structure, not bare URL parameters.

FINDING 5 — CLASS IMBALANCE
  SQL Injection: {sql_pct:.1f}%, Code Injection: {ci_pct:.1f}%
  → Handle at training time with weighted loss, not preprocessing.
""".format(
    largest_size=largest_size,
    pct_of_data=largest_size/total*100,
    n_above_5pct=clusters_above_5pct,
    n_above_1k=int((cluster_sizes > 1000).sum()),
    tr_pct=len(train_df)/total*100,
    vl_pct=len(val_df)/total*100,
    te_pct=len(test_df)/total*100,
    val_n=len(val_df),
    q_rate=quarantine_rate,
    sql_pct=global_dist.get('SQL Injection', 0)*100,
    ci_pct=global_dist.get('Code Injection', 0)*100,
))

print("RECOMMENDED PIPELINE CHANGES:")
print("  1. Replace [|;&] quarantine pattern with context-sensitive rules")
print("  2. Add cluster capping (MAX_CLUSTER_SIZE = 50-100) before splitting")
print("  3. Test threshold=0.85 for tighter near-dup clustering")
print("  4. Implement best-of-N split selection for StratifiedGroupKFold")
print(f"\n{SEP}")
print("END OF DIAGNOSTIC REPORT")
print(SEP)
