---
title: Deep Learning-Based Confidence Classification for Context-Aware Injection Alert
team: 13
document_type: Build Guide
date_generated: 2026-02-20
---

The proposed system is a deep learning-based context-aware injection alert triage system designed to detect and classify web injection attacks—including SQL Injection, Server-side Code Injection, and Other Attacks—using confidence-based classification levels (LOW below 50%, MEDIUM 50-80%, HIGH above 80%) to enable automated response actions and a 20-day retraining pipeline, with the goal of reducing false positives in Web Application Firewall deployments for the Department of Information and Communications Technology.

## Phase 1: Data Preparation and Preprocessing

### Responsible
Eugene Dela Cruz (Data & ML Lead)

### Tech Stack
PyTorch, SR-BH 2020 dataset

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Acquire the SR-BH 2020 dataset from the provided source URL.
2. Balance the dataset to 60,000 samples with 15,000 per class.
3. Address dataset quality issues including the ~10% mislabeling in benign class.
4. Implement URL decoding preprocessing.
5. Remove null bytes from payloads.
6. Normalize whitespace in input data.
7. Extract features from HTTP requests.
8. Apply MinHash/LSH deduplication.
9. Create tokenization with vocabulary size of 10,000.
10. Set maximum sequence length to 200.
11. Create PyTorch DataLoaders with stratified split.
12. Split data into 48,000 training samples.
13. Split data into 6,000 validation samples.
14. Split data into 6,000 test samples.

## Phase 2: Deep Learning Model Development

### Responsible
Eugene Dela Cruz (Data & ML Lead)

### Tech Stack
PyTorch, CNN, Bi-LSTM, DistilBERT, Hugging Face Transformers

### Target Metrics
Accuracy ≥95%, F1-Score ≥0.85 (macro), FPR ≤3%, Latency <100ms

### Checklist
1. Implement CNN + Bi-LSTM architecture.
2. Implement Bi-LSTM + Attention architecture.
3. Implement DistilBERT architecture.
4. Train models using PyTorch.
5. Set target accuracy to ≥95%.
6. Set target F1-score to ≥0.85 macro average.
7. Set target false positive rate to ≤3%.
8. Set target inference latency to <100ms.
9. Implement LOW confidence threshold below 50%.
10. Implement MEDIUM confidence threshold 50-80%.
11. Implement HIGH confidence threshold above 80%.
12. Export trained model for production deployment.
13. Export tokenizer for production deployment.
14. Implement attention visualization for BiLSTM+Attention model.

## Phase 3: Web Application Development

### Responsible
Froilan Gayao (Backend Lead)

### Tech Stack
FastAPI, PostgreSQL

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Develop FastAPI backend with RESTful endpoints.
2. Create /api/predict endpoint for single request classification.
3. Create /api/batch-predict endpoint for multiple requests.
4. Limit batch predict to maximum 100 requests per batch.
5. Create /api/alerts endpoint for paginated alert history.
6. Create /api/feedback endpoint for analyst corrections.
7. Create /api/stats endpoint for attack statistics.
8. Create /api/explain endpoint for LLM-based explanations.
9. Limit batch explanations to control API costs.
10. Implement PostgreSQL database for traffic logging.
11. Store timestamp in database.
12. Store source_ip in database.
13. Store http_request in database.
14. Store prediction in database.
15. Store confidence in database.
16. Store confidence_level in database.
17. Store action_taken in database.
18. Store analyst_label in database.
19. Create web dashboard for real-time attack visualization.
20. Create alert management interface.
21. Create analyst labeling interface.
22. Integrate lightweight LLM for attack explanations.
23. Rate-limit LLM explanations to 1-2 minutes between batches.
24. Limit maximum 100 attacks per explanation request.
25. Apply PII sanitization before sending to LLM API.
26. Implement template-based fallback explanations. (STRETCH)

## Phase 4: Automated Response System

### Responsible
Froilan Gayao (Backend Lead)

### Tech Stack
FastAPI, rate limiting, CAPTCHA

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Implement LOW confidence response with light rate limiting at 100 req/min.
2. Implement logging for analysis on LOW confidence alerts.
3. Implement MEDIUM confidence response with aggressive throttling at 20 req/min.
4. Implement mandatory CAPTCHA for MEDIUM confidence alerts.
5. Implement dashboard alerts for MEDIUM confidence.
6. Implement HIGH confidence response with immediate IP blocking.
7. Set temporary IP block duration to 1 hour.
8. Implement firewall rule enforcement for HIGH confidence.
9. Implement real-time security notifications for HIGH confidence.
10. Apply CAPTCHA only to browser-based HTTP GET traffic.

## Phase 5: ModSecurity Integration

### Responsible
Froilan Gayao (Backend Lead), Jabez Nonan (DevOps)

### Tech Stack
ModSecurity, OWASP CRS, Nginx

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Integrate with OWASP ModSecurity v3.0 or higher.
2. Integrate with OWASP Core Rule Set v4.x.
3. Develop log bridge to parse ModSecurity audit.log.
4. Feed HTTP requests from log bridge to ML model.
5. Implement hybrid detection combining CRS anomaly scores.
6. Combine CRS scores with ML confidence predictions.
7. Deploy on Ubuntu Server with Nginx reverse proxy.

## Phase 6: Retraining Pipeline

### Responsible
Froilan Gayao (Backend Lead)

### Tech Stack
PyTorch, PostgreSQL

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Implement 20-day automated retraining pipeline.
2. Collect analyst-labeled samples daily at 02:00.
3. Accumulate minimum 500 labeled samples for retraining.
4. Trigger full model fine-tuning every 20 days.
5. Collect analyst-labeled samples from production traffic.
6. Fine-tune existing model rather than training from scratch.
7. Deploy new model only if it outperforms current model.
8. Implement model versioning with timestamp-based naming.
9. Implement rollback capability for model deployment.
10. Track performance metrics per model version.

## Phase 7: Deployment Automation and Response Orchestration

### Responsible
Jabez Nonan (DevOps)

### Tech Stack
Ansible, Ubuntu Server, systemd, SSL

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Develop Ansible playbook for initial system deployment.
2. Deploy FastAPI using Ansible.
3. Deploy PostgreSQL using Ansible.
4. Deploy Nginx using Ansible.
5. Deploy ModSecurity using Ansible.
6. Develop Ansible playbook for IP blocking operations.
7. Develop Ansible playbook for IP unblocking operations.
8. Develop Ansible playbook for firewall rule updates.
9. Develop Ansible playbook for service restarts.
10. Develop Ansible playbook for configuration changes.
11. Implement Python orchestration layer in FastAPI.
12. Load trained PyTorch model for inference.
13. Classify incoming HTTP requests in orchestration layer.
14. Trigger Ansible playbooks based on confidence level.
15. Configure systemd services for FastAPI application.
16. Configure systemd services for Nginx.
17. Implement SSL setup for secure HTTPS connections.
18. Create installation documentation for DICT client.

## Phase 8: Testing and Evaluation

### Responsible
Mark Aquino (Frontend/Test/Docs), Junaid Bantuas (Frontend/Test/Docs)

### Tech Stack
Pytest

### Target Metrics
No phase-specific metric; see final integration metrics in Phase 9.

### Checklist
1. Conduct unit testing for preprocessing.
2. Conduct unit testing for model prediction.
3. Conduct unit testing for API endpoints.
4. Perform integration testing for end-to-end classification workflow.
5. Execute security testing with real attack payloads.
6. Use OWASP attack payloads for testing.
7. Use PayloadsAllTheThings attack payloads for testing.
8. Measure system performance against target metrics.
9. Validate against target accuracy of ≥95%.
10. Validate against target F1-score of ≥0.85.
11. Validate against target false positive rate of ≤3%.
12. Validate against target latency of <100ms.

## Phase 9: Model Evaluation and Analysis

### Responsible
Eugene Dela Cruz (Data & ML Lead)

### Tech Stack
PyTorch

### Target Metrics
Accuracy ≥95%, F1-Score ≥0.85 (macro), FPR ≤3%, Latency <100ms

### Checklist
1. Calculate overall accuracy against ≥95% target.
2. Calculate per-class precision.
3. Calculate per-class recall.
4. Calculate per-class F1-score against ≥0.85 target.
5. Calculate false positive rate against ≤3% target.
6. Generate confusion matrix.
7. Generate classification report.
8. Perform paired t-test at α=0.05 between model performances.
9. Use 5-fold cross-validation for RNN models.
10. Run 3 different seeds for DistilBERT.
11. Report mean and standard deviation for all metrics.
12. Document p-values for statistical significance.
13. Document per-class performance in table format.
14. Perform ablation study on model components.
15. Document and analyze misclassifications.
16. Categorize errors by type.
17. Analyze ambiguous payload errors.
18. Analyze encoding issue errors.
19. Analyze novel attack pattern errors.
20. Present representative failure cases with root cause analysis.
21. Propose mitigation strategies for identified weaknesses.

## Critical Path and 36-Week Timeline

1. Data Preparation (Weeks 1-4)
2. Model Training (Weeks 5-10)
3. Backend Integration (Weeks 11-16)
4. Deployment (Weeks 31-34)

### Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 4 | Data Ready | Cleaned dataset, DataLoaders |
| 10 | Model Selected | Trained models, comparison report, ablation study |
| 16 | Backend Complete | All API endpoints functional |
| 22 | Frontend Complete | Dashboard with visualizations |
| 26 | LLM Integrated | Attack explanations working |
| 30 | WAF Integrated | Hybrid detection operational |
| 34 | Deployed | System running on cloud server |
| 36 | Documentation Complete | Technical docs, user manual, presentation |

## Dataset Sources

| Dataset Name | URL |
|-------------|-----|
| SR-BH 2020 | https://github.com/PooKYZZZ/balanced_4class_15k |

## Consolidated Target Metrics

| Metric Name | Target Value | Source | Applicable Phase(s) |
|-------------|--------------|--------|---------------------|
| Accuracy | ≥95% | Paper, CONTEXT.md | Phase 2, Phase 9 |
| F1-Score (macro) | ≥0.85 | Paper, CONTEXT.md | Phase 2, Phase 9 |
| False Positive Rate | ≤3% | Paper, CONTEXT.md | Phase 2, Phase 9 |
| Inference Latency | <100ms | Paper, CONTEXT.md | Phase 2, Phase 9 |
| Vocabulary Size | 10,000 | Paper | Phase 1 |
| Maximum Sequence Length | 200 | Paper | Phase 1 |
| Training Samples | 48,000 (80%) | Paper | Phase 1 |
| Validation Samples | 6,000 (10%) | Paper | Phase 1 |
| Test Samples | 6,000 (10%) | Paper | Phase 1 |
| Batch Size (max) | 100 | Paper | Phase 3 |
| LOW Confidence Threshold | <50% | Paper | Phase 2, Phase 4 |
| MEDIUM Confidence Threshold | 50-80% | Paper | Phase 2, Phase 4 |
| HIGH Confidence Threshold | >80% | Paper | Phase 2, Phase 4 |
| LOW Rate Limit | 100 req/min | Paper | Phase 4 |
| MEDIUM Rate Limit | 20 req/min | Paper | Phase 4 |
| IP Block Duration | 1 hour | Paper | Phase 4 |
| Retraining Cycle | 20 days | Paper | Phase 6 |
| Minimum Samples for Retraining | 500 | Paper | Phase 6 |
