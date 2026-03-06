# Testing & Evaluation Checklist

**Why This Matters:** Testing proves your system works. For security applications, thorough testing prevents deployment of systems that miss real attacks or block legitimate users.

---

## Evaluation Metrics

### Understanding Metrics

| Metric | Formula | What It Measures | Target |
|--------|---------|------------------|--------|
| Accuracy | (TP+TN)/Total | Overall correctness | ≥ 95% |
| Precision | TP/(TP+FP | How many predicted attacks are real | ≥ 90% |
| Recall | TP/(TP+FN) | How many real attacks are caught | ≥ 90% |
| F1-Score | 2×(P×R)/(P+R) | Balance of precision and recall | ≥ 0.90 |
| FPR | FP/(FP+TN) | How often benign is marked attack | ≤ 3% |

### Why These Targets
- **Precision:** False positives block legitimate users
- **Recall:** Missed attacks are security breaches
- **F1-Score:** Balances both precision and recall
- **FPR ≤ 3%:** Industry standard for security tools

---

## Model Evaluation

### Classification Report
- [ ] Generate classification report
- [ ] Check overall accuracy
- [ ] Check per-class precision
- [ ] Check per-class recall
- [ ] Check per-class F1-score

### Confusion Matrix
- [ ] Generate confusion matrix
- [ ] Identify most confused classes
- [ ] Analyze misclassification patterns

### Per-Class Analysis
- [ ] Analyze Normal class performance
- [ ] Analyze SQL Injection class performance
- [ ] Analyze Code Injection class performance
- [ ] Analyze Other Attacks class performance

---

## Unit Testing

### Preprocessing Tests
- [ ] Test URL decoding function
- [ ] Test null byte removal
- [ ] Test whitespace normalization
- [ ] Test feature extraction
- [ ] Test tokenization
- [ ] Test label encoding

### Model Tests
- [ ] Test model output shape (batch, 4 classes)
- [ ] Test confidence range (0 to 1)
- [ ] Test prediction with valid input
- [ ] Test prediction with empty input
- [ ] Test prediction with very long input

### API Tests
- [ ] Test health endpoint
- [ ] Test predict endpoint with valid input
- [ ] Test predict endpoint with invalid input
- [ ] Test predict endpoint with missing fields
- [ ] Test batch predict endpoint
- [ ] Test feedback endpoint

---

## Integration Testing

### End-to-End Flow Tests
- [ ] Test: Attack payload → System → Block
- [ ] Test: Legitimate traffic → System → Allow
- [ ] Test: Low confidence → Rate limit
- [ ] Test: Medium confidence → Throttle
- [ ] Test: High confidence → Block

### Database Integration Tests
- [ ] Test traffic log storage
- [ ] Test alert retrieval
- [ ] Test feedback storage
- [ ] Test pagination

### ModSecurity Integration Tests
- [ ] Test combined decision logic
- [ ] Test CRS + ML both detect
- [ ] Test CRS only detects
- [ ] Test ML only detects
- [ ] Test neither detects (legitimate)

---

## Security Testing

### Attack Payload Testing Sources
- [ ] https://github.com/payloadbox/sql-injection-payload-list
- [ ] https://github.com/payloadbox/xss-payload-list
- [ ] OWASP WebGoat project
- [ ] PayloadsAllTheThings GitHub repository

### SQL Injection Tests
- [ ] Test basic SQL injection payloads
- [ ] Test UNION-based SQL injection
- [ ] Test Boolean-based SQL injection
- [ ] Test Time-based SQL injection
- [ ] Test encoded SQL injection
- [ ] Test obfuscated SQL injection

### Code Injection Tests
- [ ] Test command injection payloads
- [ ] Test PHP injection payloads
- [ ] Test template injection payloads
- [ ] Test serialized object attacks

### XSS Tests
- [ ] Test reflected XSS payloads
- [ ] Test stored XSS payloads
- [ ] Test DOM-based XSS payloads
- [ ] Test encoded XSS payloads

### Evasion Tests
- [ ] Test URL-encoded payloads
- [ ] Test double-encoded payloads
- [ ] Test Unicode-encoded payloads
- [ ] Test case variation payloads
- [ ] Test comment-injection payloads

---

## Performance Testing

### Latency Testing
- [ ] Measure single prediction latency
- [ ] Target: < 100ms per prediction
- [ ] Measure batch prediction latency
- [ ] Measure under load (100 concurrent requests)

### Throughput Testing
- [ ] Measure requests per second
- [ ] Test sustained load
- [ ] Identify bottleneck

### Resource Usage Testing
- [ ] Monitor CPU usage
- [ ] Monitor memory usage
- [ ] Monitor GPU usage (if applicable)
- [ ] Monitor disk I/O

---

## Regression Testing

- [ ] Create test suite of known attacks
- [ ] Run after each model update
- [ ] Compare results with baseline
- [ ] Alert on performance degradation

---

## Test Automation

- [ ] Set up pytest framework
- [ ] Create test configuration
- [ ] Set up test coverage reporting
- [ ] Integrate with CI/CD pipeline
- [ ] Run tests on every commit
