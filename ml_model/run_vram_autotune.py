import torch
import time

HEADROOM_MB = 256
MODEL_ID = "nreimers/MiniLM-L6-H384-uncased"
NUM_CLASSES = 4
MAX_SEQ_LEN = 128

if torch.cuda.is_available():
    total_gpu_mb = torch.cuda.get_device_properties(0).total_memory / 1024**2
    VRAM_BUDGET_MB = int(total_gpu_mb - HEADROOM_MB)
else:
    VRAM_BUDGET_MB = 5200

print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'} | GPU total MB: {total_gpu_mb if torch.cuda.is_available() else 'N/A'} | VRAM budget: {VRAM_BUDGET_MB} MB")

candidates = list(range(512, 63, -32))
best_bs = None
best_peak = 0.0

for test_bs in candidates:
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    fits = False
    peak_mb = float('inf')
    print(f"Testing bs={test_bs}...")
    try:
        m = torch.hub.load('huggingface/pytorch-transformers', 'model', MODEL_ID)
    except Exception:
        # fallback to transformers AutoModel
        from transformers import AutoModelForSequenceClassification
        m = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, num_labels=NUM_CLASSES)
    try:
        m = m.to('cuda').train()
        ids = torch.randint(0, 1000, (test_bs, MAX_SEQ_LEN), device='cuda')
        msk = torch.ones(test_bs, MAX_SEQ_LEN, dtype=torch.long, device='cuda')
        lbl = torch.zeros(test_bs, dtype=torch.long, device='cuda')
        from torch.amp import autocast
        with autocast(device_type='cuda', dtype=torch.bfloat16, enabled=True):
            out = m(input_ids=ids, attention_mask=msk, labels=lbl)
        out.loss.backward()
        peak_mb = torch.cuda.max_memory_allocated() / 1024**2
        fits = peak_mb <= VRAM_BUDGET_MB
    except RuntimeError as e:
        if 'out of memory' in str(e).lower():
            fits = False
            peak_mb = float('inf')
        else:
            raise
    finally:
        try:
            del m, ids, msk, lbl, out
        except Exception:
            pass
        torch.cuda.empty_cache()
    pct = peak_mb / VRAM_BUDGET_MB * 100 if peak_mb != float('inf') else 0
    tag = f"{peak_mb:.0f} MB  ({pct:.1f}% of budget)" if peak_mb != float('inf') else 'OOM'
    print(f"  bs={test_bs:4d} -> {tag}")
    if fits:
        best_bs, best_peak = test_bs, peak_mb
        break

if best_bs is None:
    print('No batch size >=64 fits within budget')
else:
    print(f"Selected batch size: {best_bs} | Peak: {best_peak:.0f} MB | Budget: {VRAM_BUDGET_MB} MB | Headroom left: {VRAM_BUDGET_MB-best_peak:.0f} MB")
