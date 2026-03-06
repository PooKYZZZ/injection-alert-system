# Retraining Pipeline Checklist

> **PD2 scope — deferred per pd1_pd2_boundary_statement.md**

**Why This Matters:** ML models degrade over time due to concept drift—attack patterns change, new attack types emerge, and traffic patterns evolve. Without retraining, your model will become increasingly ineffective.

---

## Data Collection System

### Traffic Logging
- [ ] Log all incoming HTTP requests
- [ ] Log model predictions and confidence
- [ ] Log actions taken
- [ ] Store in PostgreSQL database

### Database Schema
- [ ] Create traffic_logs table
- [ ] Add analyst_label column (NULL until labeled)
- [ ] Add labeled_at timestamp
- [ ] Add labeled_by field

### Labeling Interface
- [ ] Create UI for analysts to review predictions
- [ ] Allow analysts to correct model predictions
- [ ] Store corrected labels in database
- [ ] Track labeling statistics per analyst

---

## Retraining Schedule

### Configuration (Per Chapter 1 - Objective 6)
- [ ] Schedule retraining cycle: **20 days**
- [ ] Run at 2 AM (low traffic period)
- [ ] Set up cron job or Windows Task Scheduler
- [ ] **Minimum 500 labeled samples** required to trigger retraining

### Cron Setup (Linux)
```
0 2 * * * cd /opt/injection-alert-system && /opt/injection-alert-system/venv/bin/python scripts/retrain.py
```

### Task Scheduler Setup (Windows)
- [ ] Create task to run `python scripts\retrain.py` at 2 AM
- [ ] Set to run daily for 20 days

---

## Retraining Script Requirements

- [ ] Load new labeled samples from database
- [ ] Check minimum samples threshold: **≥ 500 new samples** (per Chapter 1)
- [ ] Merge with original training data
- [ ] Preprocess combined data
- [ ] Fine-tune existing model (not train from scratch)
- [ ] Evaluate on validation set
- [ ] Compare with current production model
- [ ] **Deploy only if new model outperforms current model**
- [ ] Implement model comparison (accuracy, F1, FPR)
- [ ] Notify team of deployment decision

---

## Model Versioning

### Version Tracking
- [ ] Save models with timestamp: `model_YYYYMMDD_HHMM.pt`
- [ ] Create symlink to current model
- [ ] Keep last 5 model versions
- [ ] Delete older versions to save space

### Version Directory Structure
```
models/
├── model_20260217_0200.pt
├── model_20260218_0200.pt
├── model_20260219_0200.pt
├── ...
└── current_model.pt -> model_20260219_0200.pt
```

---

## Performance Tracking

### Metrics to Track
- [ ] Version/Date
- [ ] Number of samples trained
- [ ] Accuracy
- [ ] F1-Score
- [ ] False Positive Rate
- [ ] Per-class F1-Score

### Storage Format (JSON)
```json
{
  "version": "20260217_0200",
  "date": "2026-02-17",
  "samples_trained": 48500,
  "accuracy": 0.956,
  "f1_score": 0.952,
  "false_positive_rate": 0.023,
  "per_class_f1": {
    "Normal": 0.96,
    "Code Injection": 0.94,
    "SQL Injection": 0.95,
    "Other Attacks": 0.93
  }
}
```

---

## Rollback Strategy

- [ ] Keep previous model version available
- [ ] Create rollback script
- [ ] Document rollback procedure
- [ ] Test rollback process

---

## Notifications

- [ ] Notify on successful retraining
- [ ] Notify on failed retraining
- [ ] Notify on model deployment
- [ ] Notify on rollback
- [ ] Send email/dashboard notification
