# ModSecurity Integration Checklist

> **PD2 scope — deferred per pd1_pd2_boundary_statement.md**

**Why This Matters:** ModSecurity is the most widely deployed open-source WAF. Integration with your ML model creates a hybrid system—combining rule-based detection with ML-based classification for better accuracy.

---

## ModSecurity Installation

### Ubuntu + Apache
- [ ] Install ModSecurity module
- [ ] Enable security2 module
- [ ] Restart Apache

### Ubuntu + Nginx
- [ ] Install libmodsecurity3
- [ ] Install libnginx-mod-http-modsecurity
- [ ] Enable in nginx config
- [ ] Set modsecurity rules file path
- [ ] Restart Nginx

---

## OWASP Core Rule Set (CRS)

### Installation
- [ ] Clone CRS repository from GitHub
- [ ] Copy rules to /etc/modsecurity/crs/
- [ ] Copy crs-setup.conf.example to crs-setup.conf
- [ ] Configure ModSecurity to load CRS

### CRS Configuration
- [ ] Review paranoia level (1-4, higher = more strict)
- [ ] Configure anomaly scoring mode
- [ ] Review and adjust rules for your application
- [ ] Test with legitimate traffic first

---

## ModSecurity Configuration

### Detection Mode (Initial Testing)
- [ ] Set SecRuleEngine to DetectionOnly
- [ ] Enable audit logging
- [ ] Set audit log path
- [ ] Configure audit log parts

### Production Mode (After Testing)
- [ ] Set SecRuleEngine to On
- [ ] Keep audit logging enabled
- [ ] Configure appropriate response actions

---

## ML Integration

### Log Bridge
- [ ] Create script to monitor ModSecurity audit log
- [ ] Parse ModSecurity alerts
- [ ] Extract HTTP request data
- [ ] Extract source IP
- [ ] Extract anomaly score

### Communication Methods
Choose one:
- [ ] File-based polling (watch audit.log for changes)
- [ ] Syslog forwarding (send to ML service)
- [ ] Direct API call from ModSecurity (mlogc)

### Combined Decision Logic
- [ ] Implement combined decision function
- [ ] Input: CRS anomaly score + ML prediction + ML confidence
- [ ] Output: Action (ALLOW, THROTTLE, BLOCK)

### Decision Matrix

| CRS Score | ML Confidence | Action | Reason |
|-----------|---------------|--------|--------|
| ≥ 5 | ≥ 80% | BLOCK | Both high confidence |
| ≥ 5 | 50-80% | BLOCK | CRS detected, ML agrees |
| ≥ 5 | < 50% | THROTTLE | CRS detected, ML uncertain |
| < 5 | ≥ 80% | BLOCK | ML detected, CRS missed |
| < 5 | 50-80% | THROTTLE | ML medium confidence |
| < 5 | < 50% | ALLOW | Both see as benign |

---

## Integration Testing

### Test Scenarios
- [ ] Legitimate traffic passes through
- [ ] Known SQL injection detected by both systems
- [ ] Known XSS detected by both systems
- [ ] New attack type detected by ML only
- [ ] False positive from CRS corrected by ML
- [ ] High confidence attacks are blocked
- [ ] Low confidence attacks are logged only

### Performance Testing
- [ ] Measure latency impact
- [ ] Ensure total latency < 100ms
- [ ] Test under load
- [ ] Monitor resource usage

---

## Monitoring

- [ ] Monitor ModSecurity audit log size
- [ ] Monitor ML service health
- [ ] Monitor combined decision accuracy
- [ ] Alert on integration failures
