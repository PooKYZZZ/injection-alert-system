import hashlib
from pathlib import Path

CANONICAL = [
    "train.parquet",
    "validation.parquet",
    "test.parquet",
    "quarantine_dataset.parquet",
]

base = Path('data/processed/v3_907k_cleaned')
out = base / 'checksums.txt'
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', encoding='utf8') as fh:
    fh.write("# SHA256 checksums — SRBH_clean_v3.1.0 canonical parquets\n")
    fh.write(f"# Algorithm: SHA256\n")
    for name in CANONICAL:
        p = base / name
        h = hashlib.sha256()
        with open(p, 'rb') as pf:
            while True:
                b = pf.read(65536)
                if not b:
                    break
                h.update(b)
        fh.write(f"{h.hexdigest()}  {name}\n")
print('Wrote', out)
