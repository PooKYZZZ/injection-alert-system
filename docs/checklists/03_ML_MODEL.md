# ML Model Development Checklist

**Why This Matters:** Model architecture choice affects accuracy, speed, and resource requirements. Testing multiple architectures ensures you select the best one for your specific problem.

**Hardware:** Trainable on NVIDIA RTX 3060 (6GB VRAM) or Google Colab (free T4 GPU).

---

## Target Metrics (Per Chapter 1 & 3)

| Metric | Target | Source |
|--------|--------|--------|
| Accuracy | ≥ 95% | Paper Requirements |
| F1-Score (macro) | ≥ 0.85 | Paper Requirements |
| False Positive Rate | ≤ 3% | Safety Constraint |
| Inference Latency | < 100ms | Performance Constraint |
| Model Size | < 6GB VRAM | Efficiency Constraint |
| Training Time | < 60 min | Manufacturability |

---

## MCDM Analysis Results (Per Chapter 3)

### Weighted Scores (MCDM Decision Matrix)

| Model | Weighted Score | Rank |
|-------|----------------|------|
| **DistilBERT** | **7.83** | **1 (Selected)** |
| BiLSTM+Attention | 6.02 | 2 |
| CNN+BiLSTM | 5.80 | 3 |

### Performance by Model

| Model | Accuracy | F1-Score | Latency (ms) | VRAM (MB) |
|-------|----------|----------|--------------|-----------|
| DistilBERT | 98.45% | 85.47% | 7.5 | 2,048 |
| BiLSTM+Attention | 97.50% | 85.00% | 0.8 | 768 |
| CNN+BiLSTM | 97.12% | 75.22% | 0.7 | 512 |

---

## Confidence Classification Thresholds (Per Chapter 2 & 3)

- [ ] Implement confidence level function
- [ ] Map probability outputs to confidence levels:

| Confidence Level | Probability Range | Action |
|-----------------|------------------|--------|
| LOW | < 50% | Rate limit (100 req/min) |
| MEDIUM | 50-80% | Throttle + Captcha |
| HIGH | > 80% | Block + Alert |

---

## Architecture Implementation

### 1. CNN + Bi-LSTM Architecture (Baseline)
- [ ] Implement embedding layer
- [ ] Implement CNN layers (extract local patterns/n-grams)
- [ ] Implement MaxPooling layers
- [ ] Implement Bi-LSTM layer (capture sequential context)
- [ ] Implement dense layers with dropout
- [ ] Implement output layer (4 classes, softmax)

**Architecture Notes:**
- CNN layers: Extract local patterns from HTTP requests
- Bi-LSTM layers: Capture sequential dependencies
- Standard baseline in security classification research (WAMM 2025, WADBERT 2026)
- Expected: 97% accuracy, 75% F1, <1ms latency

### 2. Bi-LSTM + Attention Architecture (Baseline)
- [ ] Implement embedding layer
- [ ] Implement Bi-LSTM with return_sequences=True
- [ ] Implement self-attention mechanism (Bahdanau attention)
- [ ] Implement global average pooling
- [ ] Implement dense layers with dropout
- [ ] Implement output layer

**Architecture Notes:**
- Attention learns which parts of the request are most important
- Best RNN-based architecture for SQL injection detection (IEEE 2025)
- Better interpretability for security analysis
- Expected: 97% accuracy, 85% F1, <1ms latency

### 3. DistilBERT Architecture (Primary - Selected via MCDM)
- [ ] Load pretrained DistilBERT from Hugging Face (`distilbert-base-uncased`)
- [ ] Implement custom classification head (4 classes)
- [ ] Configure tokenizer for HTTP payloads
- [ ] Implement fine-tuning pipeline
- [ ] Implement INT8 quantization
- [ ] Verify quantized model accuracy

**Architecture Notes:**
- 66M parameters, pretrained on 3B+ words
- Transfer learning advantage for obfuscated payloads
- State-of-the-art for text classification
- Expected: 98%+ accuracy, 85%+ F1, 5-10ms latency (quantized)
- **Selected as primary model due to highest MCDM score (7.83)**

---

## Training Configuration

### Hyperparameters (RNN Models)
| Parameter | Value | Notes |
|-----------|-------|-------|
| Embedding Dim | 128 | Size of word vectors |
| Learning Rate | 0.001 | Adam optimizer default |
| Batch Size | 32 | Balanced for memory/speed |
| Epochs | 50 | With early stopping |
| Dropout Rate | 0.5 | Prevent overfitting |
| Optimizer | Adam | Good default for NLP |

### Hyperparameters (DistilBERT)
| Parameter | Value | Notes |
|-----------|-------|-------|
| Learning Rate | 2e-5 | Standard for transformers |
| Batch Size | 16-32 | Depends on VRAM (6GB = 16) |
| Epochs | 3-5 | Fine-tuning, not from scratch |
| Warmup Steps | 500 | Learning rate warmup |
| Weight Decay | 0.01 | Regularization |
| Optimizer | AdamW | Standard for transformers |

### Training Setup
- [ ] Configure loss function: CrossEntropyLoss
- [ ] Configure optimizer: Adam (RNN) / AdamW (DistilBERT)
- [ ] Implement early stopping (patience=5)
- [ ] Implement model checkpointing
- [ ] Implement learning rate scheduler
- [ ] Set up training logging (loss, accuracy per epoch)
- [ ] Implement mixed precision (FP16) for faster training

---

## Model Comparison

- [ ] Train all 3 architectures
- [ ] Record results in comparison table:

| Model | Accuracy | F1-Score | Inference Time | Parameters | Model Size |
|-------|----------|----------|----------------|------------|------------|
| CNN+Bi-LSTM | ~97% | ~75% | <1ms | ~2-5M | ~10MB |
| Bi-LSTM+Attention | ~97% | ~85% | <1ms | ~2-5M | ~10MB |
| DistilBERT | ~98%+ | ~85%+ | 5-10ms | 66M | 67MB (quantized) |

### Selection Criteria
1. **Primary:** Highest F1-Score (balances precision and recall)
2. **Secondary:** Inference time < 100ms (for real-time use)
3. **Tertiary:** Model size for deployment

---

## Confidence Classification

- [ ] Implement confidence level function
- [ ] Map probability outputs to confidence levels:

| Confidence Level | Probability Range | Action |
|------------------|-------------------|--------|
| LOW | < 50% | Rate limit |
| MEDIUM | 50-80% | Throttle + Captcha |
| HIGH | > 80% | Block + Alert |

- [ ] Test confidence classification on validation set
- [ ] Ensure confidence correlates with prediction accuracy

---

## Model Evaluation

- [ ] Calculate overall accuracy (Target: ≥ 95%)
- [ ] Calculate per-class precision (Target: ≥ 90%)
- [ ] Calculate per-class recall (Target: ≥ 90%)
- [ ] Calculate per-class F1-Score (Target: ≥ 0.90)
- [ ] Calculate false positive rate (Target: ≤ 3%)
- [ ] Generate confusion matrix
- [ ] Generate classification report

---

## Model Export & Deployment

### RNN Models
- [ ] Save best model weights (.pt file)
- [ ] Save model architecture
- [ ] Save tokenizer/vocabulary
- [ ] Save label encoder

### DistilBERT
- [ ] Save fine-tuned model (Hugging Face format)
- [ ] Export to ONNX format
- [ ] Apply INT8 quantization
- [ ] Verify quantized model accuracy (should retain 99%+ of original)
- [ ] Test ONNX inference latency

---

## Dataset Preprocessing (Critical)

⚠️ **SR-BH 2020 has ~10% mislabeling in benign class** (per WAMM paper)

- [ ] Run regex pattern matching for known attack signatures in benign samples
- [ ] Consider LLM-guided relabeling for ambiguous samples
- [ ] Apply MinHash/LSH deduplication to remove redundant entries
- [ ] Verify class balance after cleaning
- [ ] Document data cleaning process for thesis
