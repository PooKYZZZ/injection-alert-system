import hashlib
import glob
from pathlib import Path

out = Path('data/processed/v3_907k_cleaned/checksums.txt')
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', encoding='utf8') as fh:
    for p in sorted(glob.glob('data/processed/v3_907k_cleaned/*.parquet')):
        h = hashlib.sha256()
        with open(p, 'rb') as pf:
            while True:
                b = pf.read(8192)
                if not b:
                    break
                h.update(b)
        fh.write(f"{p}\t{h.hexdigest()}\n")
print('Wrote', out)
