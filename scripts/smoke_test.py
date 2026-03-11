import sys
print('Python', sys.version)
try:
    import torch
    import numpy as np
    from transformers import AutoTokenizer, DataCollatorWithPadding
    from torch.utils.data import Dataset, DataLoader
except Exception as e:
    print('IMPORT ERROR:', e)
    raise

MODEL_IDS = {
    "minilm": "nreimers/MiniLM-L6-H384-uncased",
    "distilbert": "distilbert-base-uncased",
    "bert": "bert-base-uncased",
}

MAX_SEQ_LEN = 128

class WAFDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.max_len = max_len
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])
        enc = self.tokenizer(text, max_length=self.max_len, truncation=True, return_tensors='pt')
        return {
            'input_ids': enc['input_ids'].squeeze(0),
            'attention_mask': enc['attention_mask'].squeeze(0),
            'labels': torch.tensor(label, dtype=torch.long),
        }

# Sample data
texts = ["GET /search?q=SELECT+*+FROM+users+WHERE+id%3D1 OR 1=1 --" for _ in range(32)]
labels = [0 for _ in range(32)]

print('Loading tokenizer for MiniLM-L6...')
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_IDS['minilm'])
    print('Tokenizer loaded:', tokenizer.__class__)
except Exception as e:
    print('Tokenizer load error:', e)
    raise

collator = DataCollatorWithPadding(tokenizer=tokenizer, padding=True)

ds = WAFDataset(texts, labels, tokenizer, MAX_SEQ_LEN)
loader = DataLoader(ds, batch_size=8, shuffle=False, collate_fn=collator)

batch = next(iter(loader))
print('Batch keys:', list(batch.keys()))
print('input_ids shape:', batch['input_ids'].shape)
print('attention_mask shape:', batch['attention_mask'].shape)
print('labels shape:', batch['labels'].shape)
print('dtypes:', batch['input_ids'].dtype, batch['labels'].dtype)
print('Device available:', 'cuda' if torch.cuda.is_available() else 'cpu')
print('Smoke test completed successfully.')
