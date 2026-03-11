import pandas as pd
import glob
import sys

parquets = sorted(glob.glob('data/processed/v3_907k_cleaned/*.parquet'))
parquets = [p for p in parquets if 'audit_log' not in p]
if not parquets:
    print('No parquet files found in data/processed/v3_907k_cleaned/')
    sys.exit(1)

print('Found parquet files:')
for p in parquets:
    print(' -', p)

dfs = [pd.read_parquet(p) for p in parquets]

df = pd.concat(dfs, ignore_index=True)

cluster_sizes = df.groupby('cluster_id').size()

total_clusters = len(cluster_sizes)
singleton_clusters = (cluster_sizes == 1).sum()
singleton_ratio = singleton_clusters / total_clusters if total_clusters else 0
largest_cluster = int(cluster_sizes.max()) if total_clusters else 0

print('\nResults:')
print('Total clusters:', total_clusters)
print('Singleton clusters:', singleton_clusters)
print('Singleton ratio:', f"{singleton_ratio:.4f}")
print('Largest cluster:', largest_cluster)

print('\nTop 10 cluster sizes:')
print(cluster_sizes.sort_values(ascending=False).head(10).to_string())
