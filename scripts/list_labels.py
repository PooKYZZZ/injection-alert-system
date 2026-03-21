import csv
from collections import Counter
from pathlib import Path

DATA_DIR = Path("data/processed/v3_907k_cleaned")
FILES = ["train.csv", "validation.csv", "test.csv"]


def parse_header_mapping(header_row):
    # header_row is a list of column names; mapping entries sit between
    # 'response_content_length' and 'payload_hash' in this dataset
    try:
        start = header_row.index("response_content_length") + 1
        end = header_row.index("payload_hash")
    except ValueError:
        return []

    mappings = []
    for entry in header_row[start:end]:
        entry = entry.strip()
        if not entry:
            continue
        if " - " in entry:
            code, label = entry.split(" - ", 1)
            mappings.append((code.strip(), label.strip()))
        else:
            mappings.append((None, entry))
    return mappings


def count_labels(file_path: Path):
    counts = Counter()
    with file_path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        # final_label is expected to be the last column
        try:
            label_idx = header.index("final_label")
        except ValueError:
            # fallback: assume last column
            label_idx = len(header) - 1

        for row in reader:
            if len(row) <= label_idx:
                continue
            counts[row[label_idx].strip()] += 1
    return header, counts


def main():
    total_counts = Counter()
    mappings = None

    for fname in FILES:
        path = DATA_DIR / fname
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        header, counts = count_labels(path)
        if mappings is None:
            mappings = parse_header_mapping(header)

        print(f"\nFile: {path} -> {sum(counts.values())} rows")
        for label, cnt in counts.most_common():
            print(f"  {label}: {cnt}")

        total_counts.update(counts)

    print("\nCombined counts:")
    for label, cnt in total_counts.most_common():
        print(f"  {label}: {cnt}")

    if mappings:
        print("\nHeader label mapping (code -> name):")
        for code, name in mappings:
            print(f"  {code} -> {name}")


if __name__ == '__main__':
    main()
