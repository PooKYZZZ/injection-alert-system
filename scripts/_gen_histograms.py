"""Generate per-split and combined token-length histograms from existing CSV data."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

base = Path('data/processed/v3_907k_cleaned')
splits = ['train', 'validation', 'test']
PALETTE = {'train': 'steelblue', 'validation': 'seagreen', 'test': 'darkorange'}

for split in splits:
    arr = pd.read_csv(base / f'tokenizer_lengths_{split}.csv')['tokens'].values
    meta = json.loads((base / f'tokenizer_lengths_{split}.json').read_text())
    p95, p99 = meta['95th_percentile'], meta['99th_percentile']

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(arr, bins=80, range=(0, min(int(arr.max()) + 1, 512)),
            color=PALETTE[split], edgecolor='white', linewidth=0.3)
    ax.axvline(p95, color='orange', linestyle='--', linewidth=1.5,
               label=f'p95 = {p95}')
    ax.axvline(p99, color='red', linestyle='--', linewidth=1.5,
               label=f'p99 = {p99}')
    ax.axvline(128, color='navy', linestyle=':', linewidth=1.2,
               label='max_seq_len = 128')
    ax.set_xlabel('Token length (distilbert-base-uncased)')
    ax.set_ylabel('Count')
    ax.set_title(f'Token length distribution — {split} split  (n={len(arr):,})')
    ax.legend()
    fig.tight_layout()
    out = base / f'token_length_hist_{split}.png'
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('Wrote', out)

# Combined overlay
fig, ax = plt.subplots(figsize=(10, 5))
for split in splits:
    arr = pd.read_csv(base / f'tokenizer_lengths_{split}.csv')['tokens'].values
    ax.hist(arr, bins=80, range=(0, 512), alpha=0.55, label=split,
            color=PALETTE[split], edgecolor='none')
ax.axvline(128, color='navy', linestyle=':', linewidth=1.5,
           label='max_seq_len = 128')
ax.set_xlabel('Token length (distilbert-base-uncased)')
ax.set_ylabel('Count')
ax.set_title('Token length distribution — all splits overlay')
ax.legend()
fig.tight_layout()
out = base / 'token_length_hist_all.png'
fig.savefig(out, dpi=150)
plt.close(fig)
print('Wrote', out)
