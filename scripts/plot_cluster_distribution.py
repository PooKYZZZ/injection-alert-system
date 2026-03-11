import glob
import pandas as pd
import matplotlib.pyplot as plt

parquets = sorted(glob.glob('data/processed/v3_907k_cleaned/*.parquet'))
parquets = [p for p in parquets if 'audit_log' not in p]
if not parquets:
    raise SystemExit('No parquet files found in data/processed/v3_907k_cleaned/')

dfs = [pd.read_parquet(p) for p in parquets]
DF = pd.concat(dfs, ignore_index=True)
cluster_sizes = DF.groupby('cluster_id').size()

# Basic stats
total_clusters = len(cluster_sizes)
largest = int(cluster_sizes.max())
median = int(cluster_sizes.median())
mean = float(cluster_sizes.mean())

print(f'Total clusters: {total_clusters}')
print(f'Largest cluster: {largest}')
print(f'Median cluster size: {median}')
print(f'Mean cluster size: {mean:.2f}')

# Plot histogram (log y-axis)
plt.figure(figsize=(8,5))
cluster_sizes.hist(bins=50, log=True)
plt.xlabel('Cluster size (number of payloads)')
plt.ylabel('Frequency (log scale)')
plt.title('Cluster Size Distribution (v3_907k_cleaned)')
plt.tight_layout()

out_path = 'data/processed/v3_907k_cleaned/cluster_size_hist.png'
plt.savefig(out_path, dpi=150)
print(f'Histogram saved to: {out_path}')
