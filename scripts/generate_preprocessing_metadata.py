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
    # Copy useful fields
    metadata['pipeline_version'] = d.get('pipeline_version') or d.get('pipeline_version', '3.1.0')
    metadata['git_commit'] = d.get('git_commit') or d.get('git_commit')
    # Near-dup stats
    nd = d.get('statistics', {}).get('near_duplicate_clusters', {})
    metadata['minhash_threshold'] = nd.get('threshold')
    metadata['shingle_size'] = nd.get('shingle_size')
    metadata['minhash_num_perm'] = nd.get('num_perm')
    # counts
    counts = d.get('counts', {})
    metadata['final_rows'] = d.get('final_dataset_size') or d.get('counts', {}).get('final_rows') or None
    metadata.update({
        'audit_counts': counts,
        'near_duplicate_stats': nd,
    })
else:
    metadata['note'] = 'audit_log.json not found; please inspect pipeline output.'

# Extras: add constants from pipeline if available
try:
    import ast
    src = Path('data/clean_907k.py').read_text(encoding='utf8')
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', None) in ('MINHASH_THRESHOLD','SHINGLE_SIZE','MINHASH_NUM_PERM','MAX_CLUSTER_SIZE','SPLIT_CANDIDATE_SEEDS'):
                    metadata[target.id.lower()] = ast.literal_eval(node.value)
except Exception:
    pass

meta_out.write_text(json.dumps(metadata, indent=2), encoding='utf8')
print('Wrote', meta_out)
