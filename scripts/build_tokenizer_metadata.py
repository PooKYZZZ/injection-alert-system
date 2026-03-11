"""Build data/processed/v3_907k_cleaned/tokenizer_metadata.json from per-split JSONs."""
import json
from pathlib import Path

base = Path('data/processed/v3_907k_cleaned')
splits = ['train', 'validation', 'test']

per_split = {}
p95_values = []
for split in splits:
    d = json.loads((base / f'tokenizer_lengths_{split}.json').read_text())
    per_split[split] = d
    p95_values.append(d['95th_percentile'])

max_p95 = max(p95_values)  # 119

# Sequence length decision: p95_max = 119 → max_seq_len = 128
# p99_max across splits is 161 → 256 covers everything except absolute tail
recommended_max_seq_len = 128
safe_max_seq_len = 256

metadata = {
    "tokenizer": "distilbert-base-uncased",
    "tokenizer_type": "BertTokenizer",
    "vocab_size": 30522,
    "tokenizer_model_max_length": 512,
    "dataset_version": "SRBH_clean_v3.1.0",
    "per_split_stats": per_split,
    "max_p95_across_splits": max_p95,
    "recommended_max_seq_len": recommended_max_seq_len,
    "recommended_max_seq_len_rationale": (
        f"p95 across all splits is {max_p95} tokens. "
        f"Rounding up to the next power of two ({recommended_max_seq_len}) "
        "captures >=95% of payloads with minimal truncation. "
        f"Use {safe_max_seq_len} to capture the p99 tail (~161 tokens)."
    ),
    "histogram_files": {
        split: f"token_length_hist_{split}.png" for split in splits
    },
    "histogram_all_splits": "token_length_hist_all.png",
}

out = base / 'tokenizer_metadata.json'
out.write_text(json.dumps(metadata, indent=2), encoding='utf8')
print('Wrote', out)
