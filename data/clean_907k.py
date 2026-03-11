import pandas as pd
import numpy as np
import hashlib
import json
import os
import subprocess
import urllib.parse
import html
import unicodedata
import re
from datetime import datetime, timezone
from pathlib import Path
from sklearn.model_selection import StratifiedGroupKFold

try:
    from datasketch import MinHash, MinHashLSH
    HAS_DATASKETCH = True
except ImportError:
    HAS_DATASKETCH = False
    print("Warning: 'datasketch' not found. Near-duplicate detection will be skipped.")
    print("Run 'pip install datasketch' or 'uv pip install datasketch' to enable.")

# --- CONFIGURATION ---
RAW_DATA_PATH = Path(r'G:\Documents\PDDDD\injection-alert-system\data\raw\data_capec_multilabel.csv')
OUTPUT_DIR = Path(r'G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned')
AUDIT_LOG_PATH = OUTPUT_DIR / 'audit_log.json'

PIPELINE_VERSION = "3.1.0"
RANDOM_SEED = 42

# MinHash / LSH configuration
SHINGLE_SIZE = 5
MINHASH_THRESHOLD = 0.85
MINHASH_NUM_PERM = 128

# Cluster capping: max samples retained per near-duplicate cluster
# Prevents any single cluster from dominating splits.
# Diagnostic analysis showed the largest cluster (100k rows at threshold=0.80)
# was 30.8% of the dataset, making StratifiedGroupKFold produce degenerate
# splits (68.9/0.2/30.9). Capping to 100 + raising threshold to 0.85
# resolves this while preserving within-cluster diversity.
MAX_CLUSTER_SIZE = 100

# Best-of-N split search: try N random seeds and pick the split
# whose train/val/test ratios are closest to the 80/10/10 target.
SPLIT_CANDIDATE_SEEDS = 5

# Columns to retain in final export (transformer input + labels + tracing)
EXPORT_COLUMNS = [
    'combined_payload', 'final_label', 'payload_hash', 'cluster_id',
    # Optional debug fields (can be dropped at training time)
    'request_http_method', 'request_http_request', 'request_body',
]

# Metadata columns that must be removed to prevent leakage
METADATA_LEAK_COLUMNS = [
    'src_ip', 'dst_ip', 'src_port', 'dst_port', 'timestamp',
    'response_http_protocol', 'response_http_status_code',
    'response_http_status_message', 'response_content_length',
    'request_host', 'request_origin', 'request_referer',
    'request_user_agent', 'request_cookie', 'request_content_type',
    'request_accept', 'request_accept_language', 'request_accept_encoding',
    'request_do_not_track', 'request_connection', 'request_http_protocol',
]

# Ensure outputs directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. CAPEC Mapping Configuration — explicit priority mapping
CAPEC_PRIORITY = [
    ('66 - SQL Injection', 'SQL Injection'),
    ('242 - Code Injection', 'Code Injection'),
]

# 2. Benign Label Noise Heuristics
# Regex patterns that strongly suggest an attack payload mislabeled as Normal.
# IMPORTANT: Patterns must be context-sensitive to avoid matching normal HTTP
# traffic. Diagnostic analysis (v3.0.0) found that the bare [|;&] pattern
# matched '&' in URL query strings and form data, causing a 73.3% false
# positive rate and quarantining 43% of the Normal class.
SUSPICIOUS_PATTERNS = [
    # SQL Injection indicators
    r'\b(select|union|insert|update|delete|drop|exec|xp_)\b',
    r'\b(sleep|benchmark|waitfor)\b',
    r'1\s*=\s*1',
    r'(--|#)\s*$',            # SQL comment endings
    # XSS indicators
    r'<script',
    r'<img\b',
    r'\bonerror\b',
    r'javascript\s*:',
    # Command injection indicators — context-sensitive (require shell commands)
    # Matches: ; cat /etc/passwd  |  | ls  |  && wget  |  $( cmd )
    # Does NOT match: bare & in URLs like ?foo=1&bar=2
    r';\s*(?:cat|ls|wget|curl|rm|chmod|chown|id|whoami|uname|nc|bash|sh|python|perl|ruby|php|nslookup|ping|kill|mv|cp|mkdir|touch|echo|printf|head|tail|grep|find|awk|sed|sort|env|export|set)\b',
    r'\|\s*(?:cat|ls|wget|curl|rm|chmod|chown|id|whoami|uname|nc|bash|sh|python|perl|ruby|php|nslookup|ping|kill|mv|cp|mkdir|touch|echo|printf|head|tail|grep|find|awk|sed|sort|env|export|set)\b',
    r'&&\s*(?:cat|ls|wget|curl|rm|chmod|chown|id|whoami|uname|nc|bash|sh|python|perl|ruby|php|nslookup|ping|kill|mv|cp|mkdir|touch|echo|printf|head|tail|grep|find|awk|sed|sort|env|export|set)\b',
    r'\$\(',                  # Subshell
    # Path traversal indicators
    r'\.\.[/\\]',
    r'%2e%2e',               # Encoded traversal
    # Template injection
    r'\{\{',
]
SUSPICIOUS_REGEX = re.compile('|'.join(SUSPICIOUS_PATTERNS), re.IGNORECASE)

def get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
    except Exception:
        return "Unknown"

def canonicalize_text(text):
    """Normalize text for consistent deduplication while ignoring trivial differences."""
    if not isinstance(text, str):
        return ""
    # URL decode
    text = urllib.parse.unquote(text)
    # HTML unescape
    text = html.unescape(text)
    # Unicode normalize
    text = unicodedata.normalize('NFKC', text)
    # Remove null bytes
    text = text.replace('\x00', '')
    # Whitespace normalization & lowercase for identity hashing
    text = ' '.join(text.split()).lower()
    return text

def calculate_sha256(filepath):
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def map_capec_label(row, capec_cols):
    """Deterministic priority-based CAPEC mapping.

    Resolution order: SQL Injection > Code Injection > Other Attacks > Normal.
    Multi-label rows are resolved by the first matching priority class.
    """
    # Check priority classes first (SQL Injection, Code Injection)
    for col_name, label in CAPEC_PRIORITY:
        if col_name in capec_cols and str(row.get(col_name, '0')) == '1':
            return label

    # Check for any other identified attack
    other_capecs = [c for c in capec_cols
                    if c not in ('66 - SQL Injection', '242 - Code Injection', '000 - Normal')]
    for c in other_capecs:
        if str(row.get(c, '0')) == '1':
            return 'Other Attacks'

    return 'Normal'


class UnionFind:
    """Disjoint-set data structure for building near-duplicate clusters."""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # Path compression
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        # Union by rank
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

def clean_pipeline():
    audit_log = {
        "metadata": {
            "pipeline_version": PIPELINE_VERSION,
            "random_seed": RANDOM_SEED,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": get_git_commit(),
            "label_priority_order": "SQL Injection > Code Injection > Other Attacks > Normal",
            "minhash_config": {
                "shingle_size": SHINGLE_SIZE,
                "threshold": MINHASH_THRESHOLD,
                "num_perm": MINHASH_NUM_PERM,
            },
        },
        "counts": {},
        "statistics": {},
        "files": {}
    }

    # ---------------------------------------------------------
    # STAGE 1: Dataset Loading and Schema Validation
    # ---------------------------------------------------------
    print("Stage 1: Loading raw dataset...")
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH, low_memory=False)
    audit_log["counts"]["stage_1_initial_rows"] = len(df)

    # Schema validation: verify expected text columns exist
    required_cols = ['request_http_method', 'request_http_request', 'request_body']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise RuntimeError(f"Missing expected columns: {missing_cols}")

    text_cols = ['request_http_method', 'request_http_request', 'request_body',
                 'request_user_agent', 'request_cookie']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)

    # ---------------------------------------------------------
    # STAGE 2 & 3: Canonicalization & Malformed Request Removal
    # ---------------------------------------------------------
    print("Stage 2 & 3: Canonicalization and removing malformed rows...")
    initial_len = len(df)
    df = df[(df['request_http_method'].str.strip() != '') &
            (df['request_http_request'].str.strip() != '')].copy()

    audit_log["counts"]["stage_3_malformed_removed"] = initial_len - len(df)
    audit_log["counts"]["stage_3_remaining_rows"] = len(df)

    print("         Canonicalizing payloads...")
    df['canonical_method'] = df['request_http_method'].apply(canonicalize_text)
    df['canonical_path'] = df['request_http_request'].apply(canonicalize_text)
    df['canonical_body'] = df['request_body'].apply(canonicalize_text)

    # ---------------------------------------------------------
    # STAGE 4: Exact Duplicate Removal
    # ---------------------------------------------------------
    print("Stage 4: Removing exact duplicates...")
    df['identity_string'] = (df['canonical_method'] + " " +
                             df['canonical_path'] + " " +
                             df['canonical_body'])

    df['payload_hash'] = df['identity_string'].apply(
        lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest()
    )

    df_dedup = df.drop_duplicates(subset=['payload_hash']).copy()

    audit_log["counts"]["stage_4_exact_duplicates_removed"] = len(df) - len(df_dedup)
    audit_log["counts"]["stage_4_unique_payloads"] = len(df_dedup)
    df = df_dedup

    # ---------------------------------------------------------
    # STAGE 5: CAPEC Label Mapping (Critical — must run before quarantine)
    # ---------------------------------------------------------
    print("Stage 5: Mapping CAPEC labels...")

    # FIX: detect CAPEC columns by leading digit, not by 'capec' substring
    capec_cols = [c for c in df.columns if c.strip()[0].isdigit()]
    print(f"  Found {len(capec_cols)} CAPEC columns: {capec_cols}")

    if not capec_cols:
        raise RuntimeError("CAPEC column detection failed — no columns starting with a digit found.")

    df['final_label'] = df.apply(lambda row: map_capec_label(row, capec_cols), axis=1)

    # SAFEGUARD: verify all 4 expected classes are present
    class_dist = df['final_label'].value_counts()
    print(f"  Class distribution:\n{class_dist.to_string()}")
    audit_log["statistics"]["class_distribution_before_quarantine"] = class_dist.to_dict()

    if len(class_dist) < 4:
        raise RuntimeError(
            f"CAPEC mapping failed — expected 4 classes, got {len(class_dist)}: "
            f"{list(class_dist.index)}. Check CAPEC column detection."
        )

    # Log multi-label resolution statistics
    capec_binary = df[capec_cols].apply(lambda col: col.astype(str).map(lambda x: 1 if x == '1' else 0))
    multi_label_count = int((capec_binary.sum(axis=1) >= 2).sum())
    audit_log["statistics"]["multi_label_rows_resolved"] = multi_label_count

    # ---------------------------------------------------------
    # STAGE 6: Benign Label Noise Detection (Quarantine)
    # ---------------------------------------------------------
    print("Stage 6: Quarantining suspicious benign payloads...")
    normal_mask = df['final_label'] == 'Normal'
    suspicious_mask = df['identity_string'].str.contains(SUSPICIOUS_REGEX, regex=True)
    quarantine_mask = normal_mask & suspicious_mask

    df_quarantine = df[quarantine_mask].copy()
    df = df[~quarantine_mask].copy()

    audit_log["counts"]["stage_6_suspicious_benign_quarantined"] = len(df_quarantine)

    if len(df_quarantine) > 0:
        sample_size = min(10, len(df_quarantine))
        audit_log["statistics"]["quarantine_sample_flags"] = (
            df_quarantine['identity_string'].head(sample_size).tolist()
        )

    class_dist_final = df['final_label'].value_counts().to_dict()
    audit_log["statistics"]["class_distribution_final"] = class_dist_final

    # ---------------------------------------------------------
    # STAGE 7: Near-Duplicate Cluster Construction
    # ---------------------------------------------------------
    print("Stage 7: Near-duplicate cluster construction...")

    lsh = None  # Will hold LSH index if datasketch is available
    lsh_key_to_hash = {}  # Maps LSH key -> payload_hash for cross-split test
    if HAS_DATASKETCH and len(df) > 0:
        lsh = MinHashLSH(threshold=MINHASH_THRESHOLD, num_perm=MINHASH_NUM_PERM)
        minhashes = {}

        print(f"         Building MinHash signatures for {len(df)} payloads "
              f"(shingle_size={SHINGLE_SIZE}, num_perm={MINHASH_NUM_PERM})...")

        indices = df.index.tolist()
        texts = df['identity_string'].tolist()

        for idx, text in zip(indices, texts):
            m = MinHash(num_perm=MINHASH_NUM_PERM)
            shingles = [text[i:i + SHINGLE_SIZE].encode('utf8')
                        for i in range(max(1, len(text) - SHINGLE_SIZE + 1))]
            if shingles:
                m.update_batch(shingles)
            else:
                m.update(text.encode('utf8'))
            try:
                lsh.insert(str(idx), m)
            except ValueError:
                # Duplicate key in LSH — skip (already represented)
                pass
            minhashes[str(idx)] = m

        # Save mapping from LSH key (original index) to payload_hash
        # for use in cross-split near-dup sample test later
        lsh_key_to_hash = {str(idx): h for idx, h in zip(df.index, df['payload_hash'])}

        print("         Building near-duplicate clusters via Union-Find...")
        uf = UnionFind()

        for idx_str in minhashes:
            candidates = lsh.query(minhashes[idx_str])
            for other in candidates:
                if other != idx_str:
                    uf.union(idx_str, other)

        # Assign cluster IDs
        cluster_map = {}
        for idx_str in minhashes:
            root = uf.find(idx_str)
            cluster_map[int(idx_str)] = root

        df['cluster_id'] = df.index.map(cluster_map)

        # Compute cluster statistics
        cluster_sizes = df['cluster_id'].value_counts()
        n_clusters = len(cluster_sizes)
        n_singletons = int((cluster_sizes == 1).sum())
        largest_cluster = int(cluster_sizes.max())
        near_dup_payloads = int((cluster_sizes > 1).sum())

        audit_log["statistics"]["near_duplicate_clusters"] = {
            "total_clusters": n_clusters,
            "singleton_clusters": n_singletons,
            "non_singleton_clusters": n_clusters - n_singletons,
            "largest_cluster_size": largest_cluster,
            "payloads_in_non_singleton_clusters": int(
                cluster_sizes[cluster_sizes > 1].sum()
            ),
            "shingle_size": SHINGLE_SIZE,
            "threshold": MINHASH_THRESHOLD,
            "num_perm": MINHASH_NUM_PERM,
        }

        # Warn on very large clusters (potential scanner bias)
        LARGE_CLUSTER_THRESHOLD = 1000
        large_clusters = cluster_sizes[cluster_sizes > LARGE_CLUSTER_THRESHOLD]
        if len(large_clusters) > 0:
            print(f"  WARNING: {len(large_clusters)} clusters exceed {LARGE_CLUSTER_THRESHOLD} samples "
                  f"(largest={largest_cluster}). May bias training.")

        # Top-10 largest clusters for research reporting
        top10 = cluster_sizes.head(10)
        audit_log["statistics"]["near_duplicate_clusters"]["top_10_cluster_sizes"] = [
            int(s) for s in top10.values
        ]
        audit_log["statistics"]["near_duplicate_clusters"]["clusters_above_1000"] = len(large_clusters)

        print(f"         Clusters: {n_clusters} total, {n_singletons} singletons, "
              f"largest={largest_cluster}")

        # --- CLUSTER CAPPING ---
        # Cap oversized clusters to MAX_CLUSTER_SIZE representatives.
        # This prevents any single cluster from dominating the dataset and
        # destabilizing StratifiedGroupKFold splitting.
        # Selection is stratified within each cluster to preserve class proportions.
        pre_cap_size = len(df)
        capped_frames = []
        for cid, group in df.groupby('cluster_id'):
            if len(group) <= MAX_CLUSTER_SIZE:
                capped_frames.append(group)
            else:
                # Stratified sample within cluster to preserve label distribution.
                # Manually iterate labels to avoid pandas groupby().apply() NaN issues.
                label_counts = group['final_label'].value_counts()
                sampled_parts = []
                for label, count in label_counts.items():
                    n_sample = max(1, round(count / len(group) * MAX_CLUSTER_SIZE))
                    sampled_parts.append(
                        group[group['final_label'] == label].sample(
                            n=n_sample, random_state=RANDOM_SEED
                        )
                    )
                capped_frames.append(pd.concat(sampled_parts))
        df = pd.concat(capped_frames, ignore_index=True)
        post_cap_size = len(df)
        rows_capped = pre_cap_size - post_cap_size

        # Recompute cluster sizes after capping
        cluster_sizes_after = df['cluster_id'].value_counts()
        largest_after = int(cluster_sizes_after.max())

        audit_log["counts"]["stage_7b_cluster_cap_removed"] = rows_capped
        audit_log["counts"]["stage_7b_rows_after_cap"] = post_cap_size
        audit_log["statistics"]["near_duplicate_clusters"]["max_cluster_size_cap"] = MAX_CLUSTER_SIZE
        audit_log["statistics"]["near_duplicate_clusters"]["largest_cluster_after_cap"] = largest_after

        print(f"         Cluster capping (max={MAX_CLUSTER_SIZE}): "
              f"removed {rows_capped:,} rows, largest cluster now {largest_after}")

    else:
        # Fallback: each payload is its own cluster
        print("         datasketch not available — assigning unique clusters.")
        df['cluster_id'] = range(len(df))
        audit_log["statistics"]["near_duplicate_clusters"] = "Skipped (datasketch not installed)"

    # ---------------------------------------------------------
    # STAGE 8: Transformer Input Field & Metadata Removal
    # ---------------------------------------------------------
    print("Stage 8: Building transformer input field and removing metadata...")

    # combined_payload uses CANONICALIZED text so encoding variants
    # (e.g. %2Fetc%2Fpasswd vs /etc/passwd) collapse to the same input
    df['combined_payload'] = (df['canonical_method'] + " " +
                              df['canonical_path'] + " " +
                              df['canonical_body'])

    # Payload length statistics (before dropping anything)
    payload_lengths = df['combined_payload'].str.len()
    token_lengths = payload_lengths / 4.0

    audit_log["statistics"]["payload_length"] = {
        "mean": float(payload_lengths.mean()),
        "median": float(payload_lengths.median()),
        "max": int(payload_lengths.max()),
        "95th_percentile": float(np.percentile(payload_lengths, 95)),
        "99th_percentile": float(np.percentile(payload_lengths, 99))
    }
    audit_log["statistics"]["estimated_tokens"] = {
        "mean": float(token_lengths.mean()),
        "95th_percentile": float(np.percentile(token_lengths, 95)),
        "max": float(token_lengths.max())
    }

    # Drop metadata columns to prevent leakage
    cols_to_drop = [c for c in METADATA_LEAK_COLUMNS if c in df.columns]
    # Also drop CAPEC binary columns & internal working columns
    capec_cols_to_drop = [c for c in capec_cols if c in df.columns]
    internal_cols = ['canonical_method', 'canonical_path', 'canonical_body', 'identity_string']

    all_drop = cols_to_drop + capec_cols_to_drop + internal_cols
    df.drop(columns=[c for c in all_drop if c in df.columns], inplace=True, errors='ignore')

    # Keep only export columns (+ any debug fields present)
    final_cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    df = df[final_cols].copy()

    audit_log["statistics"]["metadata_columns_removed"] = cols_to_drop
    audit_log["statistics"]["final_columns"] = list(df.columns)

    # ---------------------------------------------------------
    # STAGE 9: Cluster-Aware Stratified Splitting (best-of-N)
    # ---------------------------------------------------------
    print("Stage 9: Cluster-aware stratified splitting (80/10/10)...")

    # Sort deterministically for reproducibility before splitting
    df = df.sort_values('payload_hash').reset_index(drop=True)

    # Drop any rows with NaN labels (safety net for groupby gaps during capping)
    nan_label_count = df['final_label'].isna().sum()
    nan_cluster_count = df['cluster_id'].isna().sum()
    if nan_label_count > 0 or nan_cluster_count > 0:
        print(f"  Dropping NaN rows: {nan_label_count} label, {nan_cluster_count} cluster_id")
        df = df.dropna(subset=['final_label', 'cluster_id']).reset_index(drop=True)

    # Ensure label/cluster types are consistent (avoid str/float comparison issues)
    df['final_label'] = df['final_label'].astype(str)
    df['cluster_id'] = df['cluster_id'].astype(int)

    # Use StratifiedGroupKFold to ensure no near-dup cluster spans splits.
    # Try SPLIT_CANDIDATE_SEEDS random seeds and pick the candidate whose
    # train/val/test proportions are closest to the 80/10/10 target.
    # This mitigates residual split imbalance from cluster size variation.
    groups = df['cluster_id'].values
    labels = df['final_label'].values
    global_dist = df['final_label'].value_counts(normalize=True)

    best_split = None
    best_score = float('inf')

    for candidate_seed in range(SPLIT_CANDIDATE_SEEDS):
        try:
            print(f"  Testing seed {candidate_seed}...", end="", flush=True)
            sgkf_outer = StratifiedGroupKFold(n_splits=5, shuffle=True,
                                              random_state=candidate_seed)
            c_train_idx, c_temp_idx = next(sgkf_outer.split(df, labels, groups))

            c_temp_df = df.iloc[c_temp_idx]
            c_temp_groups = c_temp_df['cluster_id'].values
            c_temp_labels = c_temp_df['final_label'].values

            sgkf_inner = StratifiedGroupKFold(n_splits=2, shuffle=True,
                                              random_state=candidate_seed)
            c_val_idx, c_test_idx = next(sgkf_inner.split(
                c_temp_df, c_temp_labels, c_temp_groups))

            tr_n = len(c_train_idx)
            vl_n = len(c_val_idx)
            te_n = len(c_test_idx)
            n_total = tr_n + vl_n + te_n

            # Score: distance from ideal 80/10/10 + stratification drift penalty
            ratio_err = (abs(tr_n / n_total - 0.80)
                         + abs(vl_n / n_total - 0.10)
                         + abs(te_n / n_total - 0.10))

            tr_dist = df.iloc[c_train_idx]['final_label'].value_counts(normalize=True)
            max_drift = max(
                abs(tr_dist.get(c, 0) - global_dist[c])
                for c in global_dist.index
            )
            score = ratio_err + max_drift * 2

            if score < best_score:
                best_score = score
                best_split = (candidate_seed, c_train_idx, c_val_idx,
                              c_test_idx, c_temp_idx)
            print(f" score={score:.4f}")
        except Exception as e:
            print(f" failed: {e}")
            continue

    if best_split is None:
        raise RuntimeError("No valid split found across all candidate seeds.")

    chosen_seed, train_idx, val_idx_rel, test_idx_rel, temp_idx = best_split

    train_df = df.iloc[train_idx].copy()
    temp_df = df.iloc[temp_idx]
    val_df = temp_df.iloc[val_idx_rel].copy()
    test_df = temp_df.iloc[test_idx_rel].copy()

    print(f"  Best seed: {chosen_seed} (score={best_score:.4f})")
    print(f"  Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    audit_log["counts"]["stage_9_train_split"] = len(train_df)
    audit_log["counts"]["stage_9_val_split"] = len(val_df)
    audit_log["counts"]["stage_9_test_split"] = len(test_df)
    audit_log["statistics"]["split_selection"] = {
        "candidates_tested": SPLIT_CANDIDATE_SEEDS,
        "chosen_seed": chosen_seed,
        "score": round(best_score, 6),
    }

    # ---------------------------------------------------------
    # STAGE 10: Cross-Split Leakage Verification
    # ---------------------------------------------------------
    print("Stage 10: Verifying zero cross-split leakage...")

    # Exact duplicate check
    train_hashes = set(train_df['payload_hash'])
    val_hashes = set(val_df['payload_hash'])
    test_hashes = set(test_df['payload_hash'])

    tv_exact = len(train_hashes & val_hashes)
    tt_exact = len(train_hashes & test_hashes)
    vt_exact = len(val_hashes & test_hashes)

    assert tv_exact == 0, f"Train/Val share {tv_exact} exact payload hashes"
    assert tt_exact == 0, f"Train/Test share {tt_exact} exact payload hashes"
    assert vt_exact == 0, f"Val/Test share {vt_exact} exact payload hashes"

    # Near-duplicate cluster check
    train_clusters = set(train_df['cluster_id'])
    val_clusters = set(val_df['cluster_id'])
    test_clusters = set(test_df['cluster_id'])

    tv_cluster = len(train_clusters & val_clusters)
    tt_cluster = len(train_clusters & test_clusters)
    vt_cluster = len(val_clusters & test_clusters)

    audit_log["statistics"]["cross_split_verification"] = {
        "exact_hash_overlap_train_val": tv_exact,
        "exact_hash_overlap_train_test": tt_exact,
        "exact_hash_overlap_val_test": vt_exact,
        "cluster_overlap_train_val": tv_cluster,
        "cluster_overlap_train_test": tt_cluster,
        "cluster_overlap_val_test": vt_cluster,
    }

    if tv_cluster + tt_cluster + vt_cluster > 0:
        print(f"  WARNING: {tv_cluster + tt_cluster + vt_cluster} cluster overlaps detected!")
        audit_log["statistics"]["cross_split_verification"]["status"] = "WARNING"
    else:
        print("  OK — zero exact duplicates AND zero cluster overlaps across splits.")
        audit_log["statistics"]["cross_split_verification"]["status"] = "PASS"

    # Stratification drift check: verify class proportions stayed within 2%
    dataset_dist = df['final_label'].value_counts(normalize=True)
    train_dist = train_df['final_label'].value_counts(normalize=True)
    drift_warnings = []
    for cls in dataset_dist.index:
        delta = abs(train_dist.get(cls, 0) - dataset_dist[cls]) * 100
        if delta > 2.0:
            drift_warnings.append(f"{cls}: {delta:.2f}% drift")
    if drift_warnings:
        print(f"  WARNING — stratification drift > 2%: {', '.join(drift_warnings)}")
    else:
        print("  OK — stratification drift < 2% for all classes.")
    audit_log["statistics"]["cross_split_verification"]["stratification_drift_warnings"] = drift_warnings

    # Near-duplicate cross-split sample test (empirical leakage proof)
    # The LSH was keyed by original df indices before sort/reset.
    # lsh_key_to_hash maps those keys back to payload_hash so we can
    # identify which split each LSH hit belongs to.
    if HAS_DATASKETCH and lsh is not None and len(val_df) > 0:
        train_hash_set = set(train_df['payload_hash'])
        sample_n = min(5000, len(val_df))
        val_sample = val_df.sample(n=sample_n, random_state=RANDOM_SEED)
        similar_count = 0
        for _, row in val_sample.iterrows():
            m = MinHash(num_perm=MINHASH_NUM_PERM)
            text = row['combined_payload']
            shingles = [text[i:i + SHINGLE_SIZE].encode('utf8')
                        for i in range(max(1, len(text) - SHINGLE_SIZE + 1))]
            if shingles:
                m.update_batch(shingles)
            else:
                m.update(text.encode('utf8'))
            hits = lsh.query(m)
            # Resolve LSH keys to payload_hashes, check if any land in train
            for h_key in hits:
                h_hash = lsh_key_to_hash.get(h_key)
                if h_hash and h_hash != row['payload_hash'] and h_hash in train_hash_set:
                    similar_count += 1
                    break
        similarity_rate = similar_count / sample_n * 100
        print(f"  Near-dup sample test: {similar_count}/{sample_n} val payloads "
              f"have near-dup in train ({similarity_rate:.2f}%)")
        audit_log["statistics"]["cross_split_verification"]["near_dup_sample_test"] = {
            "val_samples_tested": sample_n,
            "similar_to_train": similar_count,
            "similarity_rate_pct": round(similarity_rate, 2),
        }

    # ---------------------------------------------------------
    # STAGE 11: Export Final Datasets
    # ---------------------------------------------------------
    print("Stage 11: Exporting datasets to Parquet format...")

    train_file = OUTPUT_DIR / 'train.parquet'
    val_file = OUTPUT_DIR / 'validation.parquet'
    test_file = OUTPUT_DIR / 'test.parquet'
    full_file = OUTPUT_DIR / 'cleaned_dataset.parquet'
    quarantine_file = OUTPUT_DIR / 'quarantine_dataset.parquet'

    train_df.to_parquet(train_file, index=False)
    val_df.to_parquet(val_file, index=False)
    test_df.to_parquet(test_file, index=False)
    df.to_parquet(full_file, index=False)

    if len(df_quarantine) > 0:
        df_quarantine.to_parquet(quarantine_file, index=False)

    audit_log["files"]["train_parquet"] = {
        "path": str(train_file.name), "sha256": calculate_sha256(train_file)
    }
    audit_log["files"]["validation_parquet"] = {
        "path": str(val_file.name), "sha256": calculate_sha256(val_file)
    }
    audit_log["files"]["test_parquet"] = {
        "path": str(test_file.name), "sha256": calculate_sha256(test_file)
    }
    audit_log["files"]["full_cleaned_parquet"] = {
        "path": str(full_file.name), "sha256": calculate_sha256(full_file)
    }
    if len(df_quarantine) > 0:
        audit_log["files"]["quarantine_parquet"] = {
            "path": str(quarantine_file.name), "sha256": calculate_sha256(quarantine_file)
        }

    # ---------------------------------------------------------
    # STAGE 12: Reproducibility Metadata Logging
    # ---------------------------------------------------------
    print(f"Stage 12: Exporting Audit Log to {AUDIT_LOG_PATH}")
    with open(AUDIT_LOG_PATH, 'w') as f:
        json.dump(audit_log, f, indent=4)

    print("\n[OK] PIPELINE EXECUTION COMPLETE.")
    print("--------------------------------------------------")
    print(f"Final Class Distribution: {class_dist_final}")
    print(f"Train/Val/Test Sizes: {len(train_df)} / {len(val_df)} / {len(test_df)}")
    print(f"Total Clusters: {audit_log['statistics'].get('near_duplicate_clusters', 'N/A')}")
    print(f"Cross-split status: {audit_log['statistics']['cross_split_verification']['status']}")
    print(f"See {AUDIT_LOG_PATH} for full reproducible metadata.")

if __name__ == "__main__":
    clean_pipeline()
