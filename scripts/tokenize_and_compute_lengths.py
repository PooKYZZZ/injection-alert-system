import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('--tokenizer', default='distilbert-base-uncased')
parser.add_argument('--input', required=True)
parser.add_argument('--output-prefix', default='data/processed/v3_907k_cleaned')
parser.add_argument('--batch-size', type=int, default=256)
parser.add_argument('--max-sample', type=int, default=0)
parser.add_argument('--no-hist', action='store_true', help='Skip histogram generation')
args = parser.parse_args()

try:
    from transformers import AutoTokenizer
except Exception:
    raise SystemExit('Please install transformers (pip install transformers)')

tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

inp = Path(args.input)
split_name = inp.stem  # e.g. "train", "validation", "test"
out_prefix = Path(args.output_prefix)
out_prefix.mkdir(parents=True, exist_ok=True)

print('Loading', inp)
df = pd.read_parquet(inp)
if args.max_sample and args.max_sample < len(df):
    df = df.sample(n=args.max_sample, random_state=42).reset_index(drop=True)

lengths = []
texts = df['combined_payload'].astype(str).tolist()
for i in tqdm(range(0, len(texts), args.batch_size), desc=f'tokenising {split_name}'):
    batch = texts[i:i + args.batch_size]
    enc = tokenizer(batch, truncation=False)
    lengths.extend(len(x) for x in enc['input_ids'])

arr = np.array(lengths)
p95 = int(np.percentile(arr, 95))
p99 = int(np.percentile(arr, 99))

summary = {
    'tokenizer': args.tokenizer,
    'split': split_name,
    'n_examples': len(lengths),
    'mean_tokens': float(arr.mean()),
    'median_tokens': int(np.median(arr)),
    '95th_percentile': p95,
    '99th_percentile': p99,
    'max_tokens': int(arr.max()),
}

out_json = out_prefix / f'tokenizer_lengths_{split_name}.json'
out_csv = out_prefix / f'tokenizer_lengths_{split_name}.csv'
out_json.write_text(json.dumps(summary, indent=2), encoding='utf8')
pd.DataFrame({'tokens': lengths}).to_csv(out_csv, index=False)
print('Wrote', out_json, out_csv)

# --- Histogram ---
if not args.no_hist:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 4))
        ax.hist(arr, bins=80, range=(0, min(int(arr.max()) + 1, 512)),
                color='steelblue', edgecolor='white', linewidth=0.3)
        ax.axvline(p95, color='orange', linestyle='--', linewidth=1.4,
                   label=f'p95 = {p95}')
        ax.axvline(p99, color='red', linestyle='--', linewidth=1.4,
                   label=f'p99 = {p99}')
        ax.set_xlabel('Token length (distilbert-base-uncased)')
        ax.set_ylabel('Count')
        ax.set_title(f'Token length distribution — {split_name} split')
        ax.legend()
        fig.tight_layout()
        out_hist = out_prefix / f'token_length_hist_{split_name}.png'
        fig.savefig(out_hist, dpi=150)
        plt.close(fig)
        print('Wrote', out_hist)
    except Exception as exc:
        print(f'Warning: histogram generation failed ({exc})')
