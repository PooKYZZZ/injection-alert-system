# CyberTrace training dataset share bundle

This temporary branch packages the locally available source CSV and the processed v2 splits used by the staged DistilBERT artifact.

## Contents

- `raw/data_capec_multilabel.csv` — source CSV identified by the repository as SR-BH 2020.
- `processed/v3_907k_cleaned_model_input_v2/` — the full cleaned dataset, quarantine dataset, train/validation/test splits, preprocessing metadata, aggregate audit log, and SHA256 checksums.

The split sizes are 146,794 training rows, 18,349 validation rows, and 18,350 test rows. The model-input column is `combined_payload`; labels are in `final_label`. The Parquet exports also retain request-method, request-path, and request-body debug columns. The model-input value uses the repository's `model-input-v2-redacted` preprocessing contract. The audit log contains preprocessing and validation metadata/statistics, not per-record rows.

The source CSV has HTTP request metadata columns, including IP and cookie fields. This branch is public because the GitHub repository is public; this bundle was included at the user's direction.

## Large file handling

The raw CSV is tracked with Git LFS. Install Git LFS before cloning or fetching this branch if you need the full CSV content; without LFS, GitHub provides only the pointer file.

## Redistribution

The repository's source-data note says the original dataset license governs reuse and redistribution. Verify the original SR-BH 2020 terms before redistributing it outside this project; those terms were not independently confirmed here.
