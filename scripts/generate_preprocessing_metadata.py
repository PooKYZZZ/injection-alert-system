import json
from pathlib import Path

# Read audit_log if present
audit = Path('data/processed/v3_907k_cleaned/audit_log.json')
meta_out = Path('data/processed/v3_907k_cleaned/metadata_preprocessing.json')
meta_out.parent.mkdir(parents=True, exist_ok=True)

metadata = {
    'dataset_version': 'SRBH_clean_v3.1.0',
}
if audit.exists():
    d = json.loads(audit.read_text(encoding='utf8'))
    # Nested structure: audit_log.metadata, audit_log.counts, audit_log.statistics
    m = d.get('metadata', {})
    counts = d.get('counts', {})
    stats = d.get('statistics', {})
    nd = stats.get('near_duplicate_clusters', {})

    metadata['pipeline_version'] = m.get('pipeline_version', '3.1.0')
    metadata['git_commit'] = m.get('git_commit')
    metadata['date_generated'] = m.get('timestamp_utc')

    # MinHash / near-dup config (prefer minhash_config block, fall back to nd)
    mhcfg = m.get('minhash_config', {})
    metadata['minhash_threshold'] = mhcfg.get('threshold') or nd.get('threshold')
    metadata['shingle_size'] = mhcfg.get('shingle_size') or nd.get('shingle_size')
    metadata['minhash_num_perm'] = mhcfg.get('num_perm') or nd.get('num_perm')

    # Split seed chosen by pipeline
    metadata['split_seed'] = m.get('random_seed')

    # Final exportable row count = train + val + test
    train_n = counts.get('stage_9_train_split', 0)
    val_n = counts.get('stage_9_val_split', 0)
    test_n = counts.get('stage_9_test_split', 0)
    metadata['final_rows'] = train_n + val_n + test_n

    metadata['audit_counts'] = counts
    metadata['near_duplicate_stats'] = nd
else:
    metadata['note'] = 'audit_log.json not found; please inspect pipeline output.'

# Extras: parse pipeline constants from source if available
try:
    import ast
    src = Path('data/clean_907k.py').read_text(encoding='utf8')
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', None) in (
                    'MINHASH_THRESHOLD', 'SHINGLE_SIZE', 'MINHASH_NUM_PERM',
                    'MAX_CLUSTER_SIZE', 'SPLIT_CANDIDATE_SEEDS',
                ):
                    metadata[target.id.lower()] = ast.literal_eval(node.value)
except Exception:
    pass

meta_out.write_text(json.dumps(metadata, indent=2), encoding='utf8')
print('Wrote', meta_out)
