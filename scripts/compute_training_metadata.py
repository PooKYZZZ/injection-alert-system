import json
import pandas as pd
from pathlib import Path

inp_dir = Path('data/processed/v3_907k_cleaned')
out_json = inp_dir / 'training_metadata.json'

splits = {
    'train': inp_dir / 'train.parquet',
    'validation': inp_dir / 'validation.parquet',
    'test': inp_dir / 'test.parquet',
}

metadata = {}
for name, path in splits.items():
    if not path.exists():
        print('Missing', path)
        continue
    df = pd.read_parquet(path)
    counts = df['final_label'].value_counts().to_dict()
    total = len(df)
    lengths = df['combined_payload'].str.len()
    metadata[name] = {
        'rows': int(total),
        'class_counts': {k: int(v) for k, v in counts.items()},
        'class_percentages': {k: float(v)/total for k, v in counts.items()},
        'payload_length_chars': {
            'mean': float(lengths.mean()),
            'median': float(lengths.median()),
            '95th': float(lengths.quantile(0.95)),
            '99th': float(lengths.quantile(0.99)),
            'max': int(lengths.max())
        }
    }

out_json.write_text(json.dumps(metadata, indent=2), encoding='utf8')
print('Wrote', out_json)
