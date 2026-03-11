import argparse
from pathlib import Path
import pandas as pd
from tqdm.auto import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('--tokenizer', default='distilbert-base-uncased')
parser.add_argument('--input', required=True)
parser.add_argument('--output-prefix', default='data/processed/v3_907k_cleaned')
parser.add_argument('--batch-size', type=int, default=256)
parser.add_argument('--max-sample', type=int, default=0)
args = parser.parse_args()

try:
    from transformers import AutoTokenizer
except Exception as e:
    raise SystemExit('Please install transformers (pip install transformers)')

tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

inp = Path(args.input)
out_prefix = Path(args.output_prefix)
out_prefix.mkdir(parents=True, exist_ok=True)

print('Loading', inp)
df = pd.read_parquet(inp)
if args.max_sample and args.max_sample < len(df):
    df = df.sample(n=args.max_sample, random_state=42).reset_index(drop=True)

lengths = []
texts = df['combined_payload'].astype(str).tolist()
for i in tqdm(range(0, len(texts), args.batch_size)):
    batch = texts[i:i+args.batch_size]
    enc = tokenizer(batch, truncation=False)
    # token counts per example
    lens = [len(x) for x in enc['input_ids']]
    lengths.extend(lens)

# Save summary
import json
import numpy as np
arr = np.array(lengths)
summary = {
    'tokenizer': args.tokenizer,
    'n_examples': len(lengths),
    'mean_tokens': float(arr.mean()),
    'median_tokens': int(np.median(arr)),
    '95th_percentile': int(np.percentile(arr,95)),
    '99th_percentile': int(np.percentile(arr,99)),
    'max_tokens': int(arr.max())
}

out_json = out_prefix / f'tokenizer_lengths_{inp.name.replace('.parquet','')}.json'
out_csv = out_prefix / f'tokenizer_lengths_{inp.name.replace('.parquet','')}.csv'
out_json.write_text(json.dumps(summary, indent=2), encoding='utf8')
pd.DataFrame({'tokens': lengths}).to_csv(out_csv, index=False)
print('Wrote', out_json, out_csv)
