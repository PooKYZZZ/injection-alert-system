# Data Preparation Checklist

**Why This Matters:** Data quality determines model quality. In security applications, improper preprocessing can cause models to miss obfuscated attacks or generate false positives on legitimate traffic.

---

## Dataset Acquisition

### SR-BH 2020 Dataset
- [ ] Access Harvard Dataverse: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OGOIXX
- [ ] Download the dataset files
- [ ] Extract to `data/raw/`

**Dataset Details:**
- Real HTTP traffic from WordPress server (12 days)
- Normal traffic and CAPEC-labeled attacks
- Better than synthetic datasets - captures real-world patterns

### Balanced 4-Class Dataset
- [ ] Clone balanced version: https://github.com/PooKYZZZ/balanced_4class_15k
- [ ] Verify dataset integrity (total: 60,000 samples)
- [ ] Verify class distribution:
  - [ ] Normal: 15,000 samples
  - [ ] Code Injection: 15,000 samples
  - [ ] SQL Injection: 15,000 samples
  - [ ] Other Attacks: 15,000 samples
- [ ] Verify train/validation split:
  - [ ] Training: 48,000 samples (80%)
  - [ ] Validation: 12,000 samples (20%)

**Note:** Class balance is crucial. Imbalanced datasets cause models to favor the majority class.

---

## Data Preprocessing

### Text Cleaning for HTTP Requests
- [ ] Implement URL decoding (convert `%20` to space, `%27` to `'`, etc.)
- [ ] Remove null bytes and control characters
- [ ] Normalize whitespace
- [ ] Handle special characters appropriately

**Why:** Attack payloads often use URL encoding and special characters to bypass WAF rules. The model must see the "decoded" version to learn attack patterns.

### Feature Extraction
- [ ] Extract HTTP method (GET, POST, PUT, DELETE)
- [ ] Extract URL path
- [ ] Extract query parameters
- [ ] Extract request body (for POST requests)
- [ ] Extract User-Agent string
- [ ] Extract Content-Type header
- [ ] Combine features into single input string for model

### Tokenization and Padding
- [ ] Create vocabulary from training data
- [ ] Convert text to integer sequences
- [ ] Pad sequences to uniform length
- [ ] Save tokenizer for inference

**Recommended Parameters:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| MAX_VOCAB | 10,000 | Maximum vocabulary size |
| MAX_LEN | 200 | Maximum sequence length |
| OOV_TOKEN | `<OOV>` | Out-of-vocabulary token |

### Label Encoding
- [ ] Map class names to integers:
  - Normal → 0
  - Code Injection → 1
  - SQL Injection → 2
  - Other Attacks → 3
- [ ] Convert to one-hot encoding for multi-class classification

### Data Loaders
- [ ] Create PyTorch DataLoader for training set
- [ ] Create PyTorch DataLoader for validation set
- [ ] Add batch processing (BATCH_SIZE = 32)
- [ ] Add shuffling for training set

---

## Exploratory Data Analysis (EDA)

- [ ] Create Jupyter notebook for EDA
- [ ] Analyze class distribution (visualize with bar chart)
- [ ] Analyze request length distribution
- [ ] Identify common patterns in each attack type
- [ ] Check for data quality issues
- [ ] Document findings in `notebooks/EDA.ipynb`
