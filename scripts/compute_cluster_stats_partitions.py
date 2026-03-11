import pandas as pd
files=['data/processed/v3_907k_cleaned/train.parquet',
       'data/processed/v3_907k_cleaned/validation.parquet',
       'data/processed/v3_907k_cleaned/test.parquet']
for f in files:
    print('Loading', f)
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
cluster_sizes = df.groupby('cluster_id').size()
print('\nResults (partitions only):')
print('Total clusters:', len(cluster_sizes))
print('Singleton clusters:', int((cluster_sizes==1).sum()))
print('Singleton ratio:', f"{(cluster_sizes==1).sum()/len(cluster_sizes):.4f}")
print('Largest cluster:', int(cluster_sizes.max()))
print('\nTop 10 cluster sizes:')
print(cluster_sizes.sort_values(ascending=False).head(10).to_string())
