# Feasibility Report - Team 13

**Date:** February 09, 2026

---

## Team Composition

| Student Name | Track Elective |
| :---- | :---- |
| Aquino, Mark Angelo A. | System Administration |
| Bantuas, Junaid | Cyber Physical System |
| Dela Cruz, Eugene | Data Science |
| Gayao, Froilan | System Administration |
| Nonan, Faron Jabez | System Administration |

---

## The Problem

Web Application Firewalls (WAFs) constitute a primary defensive layer against injection-based attacks in modern web infrastructure, employing predefined rules and signatures to detect known threat patterns (OWASP Foundation, 2024). ModSecurity, paired with the OWASP Core Rule Set (CRS), is the most widely deployed open-source WAF for detecting SQL injection and server-side code injection across Apache, Nginx, and IIS environments.

Despite the maturation of WAF technology, injection vulnerabilities remain a persistent and high-impact threat. In the OWASP Top 10:2025, Injection occupies rank 5 (down from rank 3 in 2021), yet 100% of applications were tested for some form of injection, and SQL Injection alone accounts for over 14,000 documented CVEs (OWASP, 2025; NVD, 2025). The continued prevalence of injection attacks underscores the need for detection mechanisms that extend beyond static rule matching.

The core operational problem lies not in detection coverage but in enforcement precision. Modern Security Operations Centers process an average of 22,000 weekly alerts, of which approximately 68% are false positives, directly contributing to analyst fatigue and missed critical events (Yang et al., 2024; Help Net Security, 2023). Empirical evaluation of ModSecurity v3.0.4 with CRS v3.3.0 demonstrated that false positive rates escalate from 0% at Paranoia Level 1 (PL1) to 2.6% at PL2, 37% at PL3, and 60.3% at PL4 — incorrectly classifying 915 out of 1,517 legitimate requests as malicious at PL4 (Chakir & Sadqi, 2023). Quantitative evaluations confirm that increasing CRS sensitivity without contextual triage significantly increases false-positive enforcement, overwhelming security teams without proportional gains in true-positive detection (Narváez et al., 2025).

This creates a fundamental operational dilemma: organizations must choose between low-sensitivity configurations that miss sophisticated attacks (PL1–PL2) and high-sensitivity configurations that generate unmanageable false positive volumes (PL3–PL4). The proposed system addresses this dilemma by introducing a confidence-calibrated ML triage layer that operates alongside CRS, enabling higher-sensitivity rule evaluation while suppressing false-positive enforcement through confidence-gated mitigation actions.

---

## Primary System Contribution

This study contributes a **confidence-calibrated machine learning triage and automated mitigation layer** integrated with OWASP ModSecurity CRS, designed to reduce false-positive enforcement in WAF deployments. The system provides: (1) ML-based confidence scoring of CRS-flagged HTTP requests, classifying each into attack categories with calibrated probability estimates; (2) confidence-gated mitigation actions (LOW/MEDIUM/HIGH tiers) that modulate enforcement intensity based on model conviction; (3) a CRS-only baseline evaluation establishing false-positive and detection rates at PL1 and PL2 as the reference point for comparative measurement; and (4) a 20-day retraining pipeline that adapts the model to evolving traffic patterns through analyst-labeled production feedback. The ML layer does not replace CRS detection logic; it augments CRS by providing a secondary confidence assessment that modulates the intensity of automated response.

---

## Client / Prospective Client

**Primary Client:** Department of Information and Communications Technology (DICT)

DICT is the Philippine government agency responsible for developing and managing the country's information and communications technology sector, with a focus on cybersecurity. The proposed system would be used to protect government web portals and public-facing applications from injection attacks.

**Use Case:** DICT IT administrators would deploy the system to:
- Monitor HTTP traffic to government web applications
- Reduce false-positive enforcement from existing WAF deployments
- Provide analysts with confidence-scored attack classification
- Enable automated, time-bounded mitigation for high-confidence detections

**Applicability:** The system is also designed for similar organizations with limited IT security resources, including academic institutions, small-to-medium enterprises, and local government units that manage web applications but lack dedicated security operations centers (SOCs).

---

## Existing Solutions & Gap

| Designs/Solutions | Signature-Based Detection | Context-Aware Triage | ML-Enhanced Analysis | Confidence-Gated Mitigation |
| ----- | :---: | :---: | :---: | :---: |
| ModSecurity + OWASP CRS | ✔️ | ✖️ | ✖️ | ✖️ |
| ML-Augmented ModSecurity (ModSec-Learn) | ✔️ | Limited | ✔️ | ✖️ |
| ML-Enhanced ModSecurity (Ikramaputra et al., 2025) | ✔️ | Limited | ✔️ | ✖️ |
| SIEM Platforms (Wazuh) | ✔️ | Rule-based | ✖️ | ✖️ |
| **Proposed Solution** | ✔️ | ✔️ | ✔️ | ✔️ |

### Existing Solutions

**Open-Source Web Application Firewalls (ModSecurity + CRS)**
ModSecurity with OWASP CRS offers deterministic, auditable signature-based detection for SQL injection, cross-site scripting, RFI, and command injection. CRS operates through anomaly scoring at configurable paranoia levels, providing broad coverage but lacking mechanisms to modulate enforcement intensity based on detection confidence.

**ML-augmented ModSecurity research (proof-of-concept)**
Research such as ModSec-Learn demonstrates that using CRS rule outputs as ML features can improve SQL injection detection accuracy at low false-positive rates (Scano et al., 2024). A 2025 study achieved 99.04% accuracy with 1% FPR using ensemble methods (Ikramaputra et al., 2025), but relied on shallow ensemble classifiers without semantic understanding of payload context and did not implement confidence-tiered automated response.

**Open-source SIEM capabilities and limits**
SIEM tools like Wazuh centralize logs, support custom correlation, and trigger automated responses, but operate reactively on stored data and lack built-in predictive, context-aware triage for ModSecurity alerts without heavy expert rule engineering.

### Identified Gaps

**No confidence-gated enforcement layer for ModSecurity**
Existing ML work around ModSecurity remains at proof-of-concept stage and does not provide a deployable framework that modulates enforcement intensity based on calibrated model confidence. Even recent ensemble-based approaches (Ikramaputra et al., 2025) stop at classification without implementing confidence-tiered automated response — the specific gap this system addresses.

**No automated response orchestration between ML detection and infrastructure hardening**
Existing systems stop at detection or classification; they do not provide an orchestration layer where a Python-based service classifies incoming traffic and triggers pre-written Ansible playbooks for time-bounded, reversible response actions (e.g., temporary IP blocking, rate limiting adjustments).

**LLM-based explanations not integrated with ModSecurity in a privacy- and cost-aware way**
There is no open, documented architecture that takes ModSecurity alerts, applies PII-safe preprocessing, and uses an LLM to generate on-demand explanations while respecting realistic latency and API-cost constraints typical of resource-constrained institutions.

**Lack of practical end-to-end guidance for resource-constrained institutions**
Documentation and research mainly target enterprise SOC environments, offering little step-by-step guidance on how a small institutional team can integrate ModSecurity, an ML triage service, and automated response under realistic constraints on budget, staff, and latency.

---

## Proposed Title & Objectives

**Title:** Design of a Deep Learning-Based Confidence Classification for Context-Aware Injection Alert

**General Objective:**
To design and implement a confidence-calibrated deep learning triage system that classifies web injection attacks (SQL Injection, Server-side Code Injection, and Other Attacks) with calibrated probability estimates, enabling confidence-gated automated mitigation integrated with OWASP ModSecurity CRS, designed to reduce false-positive enforcement in WAF deployments.

**Specific Objectives:**

### 1. Data Preparation and Preprocessing
- Acquire the SR-BH 2020 dataset (Sureda Riera et al., 2022), comprising 907,814 HTTP requests across 13 multi-label CAPEC categories, as the original source corpus
- Construct the SRBH-335k-cleaned dataset, a derived four-class imbalanced corpus (SQL Injection, Normal, Other Attacks, Code Injection) following cleaning and deduplication
- Apply a deterministic CAPEC label mapping with the following priority order for multi-label conflict resolution:
  1. CAPEC-66 → SQL Injection
  2. CAPEC-242 → Code Injection
  3. All other CAPEC attack IDs (CAPEC-126, 88, 152, 250, 209, 274, 63, 153, 272, 248) → Other Attacks
  4. CAPEC-000 → Normal
- Given prior literature indicating ~10% potential mislabeling in the benign class (per WAMM framework, arXiv:2512.23610), heuristic validation rules will be applied to flag suspicious samples for review; flagged samples will be moved to a quarantine dataset to ensure ground truth integrity
- Implement data preprocessing pipeline including URL decoding, HTML entity decoding, Unicode normalization (NFKC), null byte removal, and whitespace normalization
- Apply exact deduplication (SHA-256) to remove structural redundancy prior to train/validation/test splitting to prevent data leakage
- Implement security-specific data augmentation for minority attack classes (applied online during training only):
  - Case toggling (e.g., `SELECT` → `SeLeCt`)
  - SQL comment insertion (e.g., `UNION SELECT` → `UNION/**/SELECT`)
  - Percent-encoding of characters (e.g., `../` → `%2e%2e/`)
  - Whitespace injection
- Create tokenization and padding mechanisms; evaluate sequence length statistics to justify `MAX_LEN` parameter (initial target: 128)
- Develop PyTorch DataLoaders with stratified split (80/10/10)

### 2. Deep Learning Model Development
- Implement and empirically evaluate three (3) fine-tuned pretrained transformer architectures for HTTP payload classification:
  - **BERT-base (Fine-tuned):** Full-capacity BERT encoder (110M parameters, Devlin et al., 2019) fine-tuned end-to-end with a linear classification head over the [CLS] token representation; serves as the high-capacity reference configuration
  - **DistilBERT (Fine-tuned):** Knowledge-distilled transformer (66M parameters, Sanh et al., 2019) fine-tuned end-to-end; serves as the balanced capacity-latency configuration optimized for CPU deployment
  - **MiniLM-L6 (Fine-tuned):** Self-attention-distilled compact transformer (22.7M parameters, Wang et al., 2020) fine-tuned end-to-end; serves as the ultra-fast triage configuration for latency-constrained environments
- No candidate model is pre-selected at this stage; final model selection will be based exclusively on empirically derived performance metrics and MCDM ranking following controlled experimentation
- All models will be evaluated under identical training conditions (same dataset splits, preprocessing, hyperparameter search space, and hardware) to enable controlled comparison
- Train models using PyTorch with the following default configuration:
  - Optimizer: AdamW with weight decay 0.01
  - Learning rate: 2e-5 (search range [2e-5, 5e-5])
  - Schedule: Linear warmup (500 steps) + linear decay
  - Batch size: 32
  - Dropout: 0.1 (increase to 0.2–0.3 if overfitting)
  - Epochs: 3–6 with early stopping on validation Macro F1 (patience=2)
  - Minimum 3 random seeds per model to report mean ± std
- Implement confidence classification with thresholds: LOW (<50%), MEDIUM (50–80%), HIGH (>80%)
- Apply temperature scaling (Guo et al., 2017) on the held-out validation set prior to threshold deployment to ensure calibrated probability outputs
- Export trained model and tokenizer for production deployment
- Target performance criteria for model selection:
  - Overall accuracy: ≥95%
  - Macro F1-Score: ≥0.85
  - False Positive Rate: ≤3%
  - Single-request inference latency: <100ms on target CPU hardware

### 3. Web Application Development
- Develop FastAPI backend with RESTful endpoints:
  - `/api/predict`: Classify single HTTP request
  - `/api/batch-predict`: Classify multiple requests (max 100 per batch)
  - `/api/alerts`: Retrieve paginated alert history
  - `/api/feedback`: Store analyst corrections for retraining
  - `/api/stats`: Display attack statistics
  - `/api/explain`: Generate LLM-based explanation for classified attack (batch-limited to control API costs)
- Integrate an external cloud-managed Supabase (PostgreSQL) database accessed via standard connection strings for traffic logging (fields: timestamp, source_ip, http_request, prediction, confidence, confidence_level, action_taken, analyst_label)
- Implement a comprehensive web dashboard using Next.js 15 (App Router) and TypeScript 5.x, spanning 11 functional views (e.g., SOC Dashboard, Alert History, ML Health, Audit Trail, Administrative Settings) for real-time attack visualization and analyst workflow management
- Enforce a strict frontend security architecture leveraging Next.js API route handlers to proxy all requests to the FastAPI backend and Groq LLM API, ensuring the browser never communicates directly with internal ML or database services
- Implement role-based access control (Analyst and Admin roles) utilizing NextAuth.js v5 with JWTs securely stored in httpOnly cookies
- Mitigate DOM-based cross-site scripting (XSS) risks by rendering all intercepted attack payloads exclusively within safe code formatting blocks (`<pre><code>`) rather than allowing raw DOM insertion
- Integrate lightweight LLM (e.g., Groq API with Llama 3.1 8B) for generating human-readable attack explanations:
  - Rate-limited to 1–2 minutes between batch explanations or max 100 attacks per request
  - Example output: "This request contains SQL injection attempting to bypass authentication via UNION-based payload"
  - PII sanitization applied before sending to LLM API
  - **Note:** LLM integration is a non-critical stretch goal; fallback is template-based explanations using attack class and confidence level

### 4. Automated Response System and Hybrid Enforcement Policy
- Implement confidence-based mitigation actions:
  - **LOW confidence (<50%):** Light rate limiting (100 req/min), logging for analysis
  - **MEDIUM confidence (50–80%):** Aggressive throttling (20 req/min), mandatory captcha for browser-based sessions, dashboard alerts with analyst notification
  - **HIGH confidence (>80%):** Temporary IP blocking (1-hour default, configurable), firewall rule enforcement, real-time security notifications

  CAPTCHA enforcement applies to browser-based HTTP GET traffic where a human session can be identified, consistent with industry WAF practice (Amazon Web Services, 2024). For non-browser API traffic or automated tools where CAPTCHA challenge responses cannot be processed, rate limiting and HTTP 429 throttling serve as the primary response mechanism.

#### Hybrid Enforcement Hierarchy

The system implements a layered enforcement hierarchy in which CRS remains the primary detection engine and the ML model determines mitigation intensity:

1. **CRS as primary rule engine:** All incoming HTTP requests are first evaluated by ModSecurity CRS. CRS anomaly scoring and rule matching operate independently of the ML layer. The ML model does not override, disable, or modify CRS detection rules.
2. **ML as confidence-scoring layer:** Requests flagged by CRS are passed to the ML model for secondary classification and confidence scoring. The ML model processes only CRS-flagged traffic; it does not independently evaluate non-flagged requests. The ML model assigns a class label and calibrated probability estimate.
3. **Confidence-gated mitigation:** The ML confidence score determines the intensity of the automated response, not whether an attack was detected. CRS detection triggers the triage pipeline; ML confidence determines the enforcement tier (LOW/MEDIUM/HIGH). The ML layer does not invalidate CRS detection—it modulates only the enforcement intensity.
4. **Human-in-the-loop escalation:** All LOW and MEDIUM confidence classifications are surfaced to analysts via the dashboard. HIGH confidence actions are logged and reviewable. No enforcement action is permanent without administrator review.

#### Automation Safeguards

All automated mitigation actions are subject to the following safeguards:

| Safeguard | Implementation |
|-----------|---------------|
| **Time-bounded blocks** | HIGH-confidence IP blocks are temporary (default: 1 hour) and automatically expire; duration is configurable by administrators |
| **Full audit logging** | Every automated action (rate limit, throttle, block) is logged to PostgreSQL with timestamp, source IP, confidence score, action taken, and expiration time |
| **No permanent rule modification** | Automated actions do not modify CRS rules, ModSecurity configuration, or firewall policies permanently; all changes are ephemeral and reversible |
| **Administrator override** | Administrators can manually unblock IPs, adjust confidence thresholds, or disable automated responses at any time via the dashboard |
| **Rollback capability** | All time-bounded actions include automatic expiration; manual rollback is available for any action through the admin interface |

#### Confidence Threshold Rationale

The LOW/MEDIUM/HIGH tier structure is a concrete instantiation of **selective classification** — a formally established decision framework in which a classifier acts on high-confidence predictions, defers moderate-confidence predictions for human review, and minimally responds to low-confidence predictions to limit false enforcement (Canas et al., 2021; Xin et al., 2021). In selective classification theory, the MEDIUM tier corresponds to the *abstention region*, where model conviction is insufficient for automated action and human escalation is prescribed; the HIGH tier corresponds to the *accept-and-act region* where calibrated confidence exceeds the risk threshold for enforcement (Xin et al., 2021). This framework has been applied in analogous high-stakes text classification settings — including cybersecurity NLP triage, where high-risk model predictions are routed to human analysts while low-risk cases are handled automatically (Ioannou et al., 2023) — and in uncertainty-aware web attack detection, where uncertainty estimates have been shown to gate enforcement decisions and reduce false automated blocking (Zhou et al., 2024).

The thresholds (50%, 80%) were selected based on the following considerations:

| Threshold | Rationale |
|-----------|-----------|
| **<50% (LOW)** | On a 4-class problem, 50% probability is the majority-class chance boundary; a score near 25% indicates near-random guessing. In selective classification terms, predictions below 50% fall below the minimum conviction threshold and are routed to the monitoring tier rather than automated enforcement — consistent with prescribing abstention at the lower confidence boundary (Canas et al., 2021). |
| **50–80% (MEDIUM)** | Represents the abstention zone: model conviction is present but insufficient for automated blocking. Corresponds to the defer-to-analyst region in selective prediction frameworks, where confidence scores are used to route uncertain examples to human review rather than automated action (Xin et al., 2021). Throttling and mandatory analyst notification are applied in lieu of blocking. |
| **>80% (HIGH)** | Corresponds to the accept-and-act region in selective classification, where the model's calibrated confidence exceeds the threshold for automated enforcement. Yu et al. (2025) demonstrated across 6,689 clinical AI cases that predictions in the 70–79% range were rejected by domain experts 99.3% of the time while predictions in the 90–99% range were accepted 98.3% of the time, supporting the 80% region as a defensible inflection point between uncertain and high-conviction predictions in high-stakes automated systems. Temporary IP blocking with automatic expiration is applied at this tier. |

A critical precondition for any threshold-based enforcement scheme is that confidence scores reflect true class probabilities. Raw softmax outputs from deep neural networks are known to be systematically overconfident and do not, without correction, constitute calibrated probability estimates (Guo et al., 2017). This overconfidence problem directly motivates the calibration commitment described below — specifically, that ECE-guided temperature or Platt scaling is applied prior to threshold deployment to ensure that a stated 80% confidence score corresponds to an empirically meaningful probability of correct classification (Guo et al., 2017; Talpini et al., 2024).

The 50% and 80% values are initial operational priors consistent with selective classification practice and will be treated as starting parameters subject to empirical refinement. Threshold adjustment will be guided by precision–recall tradeoff analysis and Expected Calibration Error measurements on the validation set prior to any enforcement deployment.

##### False-Positive Suppression Mechanism

The system implements a tiered enforcement model where ML confidence directly gates the aggressiveness of automated response while preserving full logging at all tiers:

| Confidence Tier | ML Output | Mitigation Action | Logging |
|-----------------|-----------|------------------|--------|
| **LOW** | <50% probability | Light rate limiting (100 req/min), monitoring enabled | Full logging preserved; alert surfaced to dashboard for analyst review |
| **MEDIUM** | 50–80% probability | Aggressive throttling (20 req/min), CAPTCHA challenge, dashboard alerts | Full logging preserved; mandatory analyst notification |
| **HIGH** | >80% probability | Temporary IP block (1-hour default), firewall rule enforcement | Full logging preserved; real-time security notification |

**Key suppression behavior:** LOW-confidence output suppresses aggressive enforcement actions (blocking, CAPTCHA) while preserving complete audit logging. This mechanism is designed to minimize service disruption to legitimate users from potentially false-positive detections, while capturing all triage decisions for post-incident analysis. The tiered approach is consistent with the recommendation by Talpini et al. (2024) that IDS systems must quantify uncertainty and gate automated actions through calibrated confidence thresholds with human escalation at intermediate tiers. All mitigation actions are time-bounded and automatically reversible upon expiration.

The operational value of confidence-tiered alert response is supported by prior work: Gelman et al. (2023) demonstrated that ML-driven alert prioritization in real SOC environments reduces time-to-response by 22.9% and suppresses 54% of false positives while maintaining a 95.1% detection rate, supporting the design rationale for the LOW/MEDIUM/HIGH confidence tier architecture. The proposed system aims to reduce actionable false-positive enforcement relative to CRS-only deployments; quantitative reduction will be determined empirically during evaluation and compared against a CRS-only baseline configuration.

**Calibration:** Calibration evaluation will be performed using 10-bin reliability diagrams and Expected Calibration Error (ECE) computed on the validation set prior to threshold deployment. Calibration assessment will be conducted before any automated response rules are finalized, ensuring that confidence tiers reflect statistically meaningful probability estimates rather than raw softmax outputs (Guo et al., 2017). If model calibration is poor (e.g., overconfident on wrong predictions), temperature scaling or Platt scaling will be applied to ensure softmax probabilities are meaningful.

### 5. ModSecurity Integration
- Integrate with OWASP ModSecurity v3.0+ (maintained by OWASP since Trustwave EOL in July 2024) and OWASP Core Rule Set (CRS) v4.x
- Develop log bridge to parse ModSecurity audit.log and feed HTTP requests to ML model
- Implement hybrid enforcement logic where CRS anomaly scores trigger the triage pipeline and ML confidence determines mitigation intensity
- Deploy via Docker Compose on a single Ubuntu cloud VM utilizing a structured three-container architecture: ModSecurity and Nginx act as the sole internet-facing entry point (Container 1), inspecting all inbound traffic before proxying requests securely to the FastAPI application (Container 2) and Next.js frontend (Container 3) running on isolated internal networks

### 6. Retraining Pipeline
- Implement 20-day automated retraining pipeline:
  - Daily collection of analyst-labeled samples at 02:00; full model fine-tuning and deployment evaluation triggered every 20 days upon accumulation of sufficient labeled samples (target: 500+)
  - Collect analyst-labeled samples from production traffic
  - Fine-tune existing model (not train from scratch)
  - Deploy only if new model outperforms current production model
- Implement model versioning with timestamp-based naming and rollback capability
- Track performance metrics per model version

#### 20-Day Cycle Rationale
The 20-day retraining cycle was selected based on:
1. **Sample accumulation:** Estimated minimum 500 analyst-labeled samples needed for meaningful fine-tuning; at ~25 labels/day (conservative), 20 days provides sufficient data
2. **Model drift risk:** Studies show ML models can degrade 10–35% in accuracy over 6 months without retraining (Vela et al., 2022); 20-day cycles mitigate drift while allowing sufficient data collection
3. **Operational balance:** More frequent retraining (e.g., daily) risks overfitting to recent traffic patterns; less frequent (e.g., monthly) risks performance degradation

Retraining will be triggered only if the minimum labeled-sample threshold is met. If insufficient analyst feedback is accumulated within the 20-day window, the retraining cycle will extend automatically until the threshold is satisfied. This prevents underpowered fine-tuning and mitigates overfitting to limited recent samples.

This is further supported by security-specific research demonstrating that ML-based intrusion detection systems experience concept drift within days to weeks as attack patterns evolve, necessitating continuous adaptation strategies rather than static deployment (Kuppa & Le-Khac, 2022).

### 7. Deployment Automation and Response Orchestration
- Develop pre-written Ansible playbooks for infrastructure tasks:
  - Initial Ubuntu VM provisioning and Docker Compose environment setup (three-container stack: ModSecurity + Nginx + OWASP CRS, FastAPI + PyTorch models, Next.js 15 frontend) — replacing manual service-by-service installation
  - Temporary IP blocking/unblocking operations (time-bounded, auto-expiring)
  - Rate-limiting adjustments
  - Service restarts and configuration changes
- Execute a progressive four-stage deployment methodology:
  - **Stage 1 (Local):** Local developer environments running Docker Compose matching production
  - **Stage 2 (PD1):** Cloud VM deployment utilizing a high-efficiency model (e.g., MiniLM-L6) with ModSecurity in DetectionOnly mode for safe initial demonstration
  - **Stage 3 (PD2):** Full-capacity cloud deployment utilizing the optimal model with ModSecurity operating in Enforcement mode and full Ansible automation enabled
  - **Stage 4 (Handoff):** Final deployment seamlessly transitioning the Docker environment directly to DICT infrastructure
- Implement Python orchestration layer in FastAPI that:
  - Loads the trained PyTorch model for inference
  - Classifies incoming HTTP requests
  - Triggers appropriate Ansible playbooks based on confidence level
  - Example: HIGH confidence attack → call Ansible playbook for temporary IP block (1-hour default)
- Implement SSL termination setup for secure HTTPS connections on the Nginx internet-facing container
- Create installation documentation for target client (DICT)

### 8. Testing and Evaluation
- Conduct unit testing for preprocessing, model prediction, and API endpoints
- Perform integration testing for end-to-end classification workflow
- Execute security testing with real attack payloads from OWASP and PayloadsAllTheThings
- Measure and validate system performance against empirically determined targets

### 9. Model Evaluation and Analysis
- Calculate overall classification accuracy
- Calculate per-class precision, recall, and F1-score (macro average)
- Calculate false positive rate
- Generate confusion matrix and classification report

#### Statistical Significance Testing
- Perform paired t-test (α=0.05) between model performances
- Use k-fold cross-validation or multiple seeded runs (as appropriate per model architecture) to obtain performance distributions
- Report mean ± standard deviation for all metrics
- Document p-values to establish whether performance differences are statistically significant

#### Planned Experimental Repetition Protocol
Because transformer fine-tuning introduces stochastic variability (random initialization seeds, data shuffling, dropout), each candidate model will be trained under a minimum of five (5) independent random seeds to obtain performance distributions. Statistical comparison will be conducted using paired tests across identical dataset splits and random seeds. Where appropriate, McNemar's test will be applied on test-set predictions to compare classification differences between models. Final statistical procedures will be selected based on empirical distribution characteristics observed during experimentation (e.g., normality assumptions).

#### Baseline Evaluation
A CRS-only baseline will be established by evaluating ModSecurity CRS at Paranoia Levels 1 and 2 against the test dataset to measure standalone detection rates and false-positive rates. This baseline serves as the reference point for quantifying the incremental benefit of the hybrid CRS+ML system. All comparative claims regarding false-positive reduction or detection improvement will be measured against this CRS-only baseline under identical test conditions.

#### Preliminary Model Comparison Results

The following results were obtained from initial PD1 training runs on an earlier experimental balanced dataset (~60k samples; ~15k per class) under identical conditions.

| Model | Backbone | Accuracy | Precision | Recall | F1 (Weighted) | ROC-AUC | Train Time (s) | Train Time (min) |
|-------|----------|----------|-----------|--------|---------------|---------|----------------|------------------|
| BERT | bert-base-uncased | 0.9752 | 0.9754 | 0.9752 | 0.9753 | 0.9988 | 38,504.8 | 641.75 |
| DistilBERT | distilbert-base-uncased | 0.9750 | 0.9752 | 0.9750 | 0.9750 | 0.9990 | 8,500.9 | 141.68 |
| MiniLM | all-MiniLM-L6-v2 | 0.9698 | 0.9701 | 0.9698 | 0.9698 | 0.9985 | 2,147.0 | 35.78 |

> [!IMPORTANT]
> These preliminary results were obtained on an earlier balanced dataset construction during PD1. Final evaluation will be conducted on the revised SRBH-335k-cleaned dataset using the full imbalanced corpus with class-weighted loss. Macro F1, per-class precision/recall, and confusion matrices will be reported as primary metrics. Weighted F1 alone is insufficient for security classification tasks where rare attack classes are critical.

**Observations:**
- All three models exceed 96.9% accuracy on the 4-class classification task.
- BERT achieves the highest F1 (0.9753) and accuracy (0.9752), at the cost of the longest training time (641.75 min).
- DistilBERT achieves the highest ROC-AUC (0.9990) with a 4.5× reduction in training time vs. BERT.
- MiniLM achieves the fastest training time (35.78 min) — approximately 18× faster than BERT — at a modest accuracy reduction of 0.54 percentage points.

#### Per-Class Performance Analysis
| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Normal | TBD | TBD | TBD | TBD |
| SQL Injection | TBD | TBD | TBD | TBD |
| Code Injection | TBD | TBD | TBD | TBD |
| Other Attacks | TBD | TBD | TBD | TBD |

Note: Per-class breakdown will be finalized following complete evaluation with per-class confusion matrix reporting.

#### Ablation Study
Systematically remove or modify components to understand their contribution:

| Experiment | Purpose | Expected Insight |
|------------|---------|------------------|
| Best-performing model w/o pretraining | Train from random weights | Quantifies transfer learning benefit |
| Best-performing model frozen layers | Freeze bottom N layers | Identifies which layers matter most |
| Reduced sequence length | Truncate input to shorter lengths | Determines sensitivity to payload length |
| Truncation strategy | Compare right-truncation vs. left-truncation | Evaluates whether attack payloads at sequence boundaries are lost |
| Imbalance handling | Compare class-weighted CE vs. Focal Loss vs. oversampling | Identifies optimal strategy for severe class imbalance (16:1 ratio) |
| Data augmentation | Train with/without security-specific augmentation | Measures improvement on evasion/obfuscated payloads |
| Classification head | Compare [CLS] pooling vs. mean pooling vs. max pooling | Determines optimal token aggregation strategy for fine-tuned classification |

#### Failure Case Analysis
- Document and analyze misclassifications
- Categorize errors by type: ambiguous payload, encoding issue, novel attack pattern
- Present representative failure cases with root cause analysis
- Propose mitigation strategies for identified weaknesses

---

## System Architecture

This study proposes the empirical evaluation of three fine-tuned pretrained transformer architectures — BERT-base (Fine-tuned), DistilBERT (Fine-tuned), and MiniLM-L6 (Fine-tuned) — as candidate models for the confidence-calibrated triage layer of the proposed web application firewall machine learning system. Each architecture leverages a pretrained transformer encoder that is fine-tuned end-to-end on the domain-specific HTTP payload classification task. Classification is performed via a linear projection head applied to the encoder's [CLS] token output, following the standard fine-tuning paradigm established by Devlin et al. (2019). The selection of these three configurations is motivated by distinct but complementary considerations: representational capacity, parameter efficiency, CPU-feasible inference latency, and empirical precedent from the web attack detection literature.

### Model Architecture Selection and Justification

#### Transformer Backbone Justification

The transformer backbone shared across all three configurations derives from the foundational architecture introduced by Devlin et al. (2019), whose bidirectional encoder representations from transformers (BERT) substantially advanced the state of the art in natural language understanding by enabling deep bidirectional contextual encoding of input token sequences. BERT-base, comprising twelve encoder layers and approximately 110 million parameters, has since been applied extensively in cybersecurity natural language processing tasks. Seyyar et al. (2021) demonstrated that a BERT-based classification framework trained on the CSIC2010, FWAF, and HttpParams datasets achieved an F1-score of 98.70% and a reported per-request detection latency of approximately 0.4 milliseconds, providing direct empirical evidence of BERT's viability for structured web payload classification. Similarly, Su and Su (2023) reported that BERT-based models for malicious URL identification achieved macro-averaged F1-scores of 0.984 and accuracy of 98.8% on public phishing URL datasets, establishing BERT-family encoders as a consistent and defensible choice for HTTP-adjacent classification tasks. These results collectively justify BERT-base as a high-capacity reference architecture against which compressed alternatives can be meaningfully benchmarked within the proposed system.

The DistilBERT architecture (Sanh et al., 2019) represents the knowledge-distillation compression paradigm, in which a compact six-layer student model is trained to reproduce the output behavior of BERT-base using task-agnostic distillation. With approximately 66 million parameters, DistilBERT retains an estimated 97% of BERT-base's language modeling performance on benchmark evaluations while operating at approximately 60% of the parameter count and achieving a reported 1.6 times inference speedup (Sanh et al., 2019). Shen et al. (2022) further demonstrated that DistilBERT inference on CPU-only hardware can be substantially optimized through quantization and ONNX Runtime compilation, though exact millisecond-per-request figures under standardized single-server conditions are not consistently reported in the prior security literature. For the proposed deployment context — a single Ubuntu server without guaranteed GPU availability — DistilBERT's compression ratio presents a substantive practical advantage over BERT-base in memory footprint and expected throughput under CPU-constrained operation.

The MiniLM-L6 architecture (Wang et al., 2020) employs a distinct compression strategy termed deep self-attention distillation, in which the student model is trained to replicate the self-attention distributions of the teacher model's final transformer layer rather than its token-level output representations. This mechanism produces a six-layer model with approximately 22.7 million parameters, representing the most compact of the three candidate backbones. Wang et al. (2020) established that this attention-transfer approach preserves downstream task performance more effectively per parameter than output-level distillation alone. Latency measurements specific to MiniLM-L6 in web attack or HTTP payload classification scenarios are not consistently reported in the literature reviewed; however, the architecture's parameter count is approximately one-fifth that of BERT-base, and it has been deployed in latency-sensitive similarity and semantic matching applications that prioritize throughput on CPU hardware. For the proposed system, MiniLM-L6 is positioned as the ultra-fast front-line triage candidate suitable for high-request-volume environments where inference latency is the dominant operational constraint.

#### Fine-Tuning Strategy

Standard transformer fine-tuning (Devlin et al., 2019) is employed for all three candidate architectures. The pretrained encoder weights are updated end-to-end during training on the domain-specific HTTP payload classification task, with a task-specific linear classification head appended to the [CLS] token representation. This approach leverages the full contextual encoding capacity of each transformer backbone without introducing additional architectural complexity, and has been shown to achieve state-of-the-art results on text classification benchmarks with minimal task-specific engineering (Devlin et al., 2019; Sun et al., 2019).

Fine-tuning hyperparameters — including learning rate, warmup schedule, and dropout — are specified in Objective 2 above and will be held constant across all three candidate architectures to enable controlled comparison.

#### Parameter Size, Representational Capacity, and CPU Feasibility

BERT-base, with approximately 110 million parameters, provides the highest representational capacity among the three candidate backbones. Its depth and embedding dimensionality enable encoding of complex syntactic and semantic dependencies within HTTP payloads; however, its parameter count imposes the greatest memory and compute cost during inference. On CPU hardware, BERT-base inference on short sequences can remain within operationally acceptable latency bounds, as demonstrated by Seyyar et al. (2021), though exact figures under standardized single-Ubuntu-server conditions are not uniformly reported in the prior literature. Within the proposed system, fine-tuned BERT-base is positioned as a higher-capacity secondary analysis candidate, appropriate for triage scenarios where classification precision is weighted above inference speed and server resources permit the additional overhead.

DistilBERT, at approximately 66 million parameters, occupies a middle ground between representational capacity and computational cost. The architecture is explicitly designed for CPU-feasible deployment, and Sanh et al. (2019) established its speedup advantage empirically. Serialized for ONNX Runtime execution, fine-tuned DistilBERT is expected to provide a balanced configuration suitable for the primary triage role under the proposed single-server, CPU-first deployment constraint. Latency measurements for DistilBERT specifically on HTTP payload tasks are not consistently reported in the reviewed literature, and such measurements will be obtained empirically as part of the proposed system's evaluation phase.

MiniLM-L6, at approximately 22.7 million parameters, imposes the smallest memory and compute footprint of the three architectures. Its design explicitly targets resource-constrained inference environments, and the parameter count allows for faster forward passes and reduced memory bandwidth demand during CPU inference. The substantially smaller model also reduces cold-start latency during service initialization, which is relevant for a single-server deployment where no model serving infrastructure abstracts the inference process. Fine-tuned MiniLM-L6 is therefore positioned as the ultra-fast triage configuration, most appropriate for the front-line classification of high-volume CRS-flagged request streams where latency constraints are stringent and a modest reduction in representational capacity is acceptable given the calibrated probability output that downstream enforcement tiers require.

#### Probability Calibration Commitment

A critical operational requirement shared across all three fine-tuned configurations is the production of well-calibrated probability outputs for enforcement tier assignment. Raw softmax outputs from deep neural networks are systematically overconfident and do not, without correction, constitute valid probability estimates of classification accuracy (Guo et al., 2017). Because the proposed system assigns enforcement actions directly based on confidence tier thresholds (LOW below 50%, MEDIUM between 50% and 80%, and HIGH above 80%), it is essential that a stated output probability of 80% reflects a substantively accurate empirical probability of correct classification rather than a miscalibrated network activation. Accordingly, temperature scaling as described by Guo et al. (2017) will be applied to each fine-tuned model on the held-out validation set prior to any threshold-based enforcement deployment. Expected Calibration Error will be computed using ten-bin reliability diagrams to assess and document the calibration quality of each model before the enforcement policy is finalized. This calibration procedure applies uniformly to all three fine-tuned configurations and constitutes a binding methodological commitment rather than an optional post-processing step.

#### Comparative Evaluation Rationale

The concurrent evaluation of fine-tuned BERT-base, DistilBERT, and MiniLM-L6 constitutes a structured empirical comparison across three levels of the parameter-capacity spectrum within a unified fine-tuning framework. By holding the classification head design (linear projection over [CLS]), the calibration procedure, and all training hyperparameters constant across all three configurations and varying only the transformer backbone, the proposed evaluation isolates the contribution of encoder capacity and compression strategy to classification performance, inference latency, and calibration quality under identical hardware and dataset conditions. This comparison enables the feasibility study to determine empirically whether the representational depth of BERT-base is operationally necessary for the proposed triage task, whether DistilBERT's distillation provides a defensible capacity-latency tradeoff for the primary deployment role, and whether MiniLM-L6 achieves sufficient classification performance to serve as the front-line ultra-fast triage option. The outcome of this evaluation will directly inform the MCDM-based model selection procedure and will determine which configuration is deployed into the production confidence-gated enforcement pipeline.

Recurrent neural network architectures (e.g., CNN+BiLSTM, BiLSTM+Attention) are acknowledged in the broader injection detection literature as prior-generation approaches. Studies such as the WAMM framework (Sanhour et al., 2025) and WADBERT (Zhang et al., 2026) have demonstrated that transformer-based models exhibit competitive or superior performance on web attack classification benchmarks relative to RNN-based alternatives. This study takes these findings as established context and proceeds with a focused fine-tuned transformer comparison, evaluating which backbone compression strategy best satisfies the operational requirements of the proposed system under identical experimental conditions.

No empirical claims regarding relative model performance are presented in this feasibility study; all comparative evaluations will be conducted during PD1 under identical experimental conditions.

---

## Dataset and Preprocessing

### Original Dataset
The SR-BH 2020 dataset (Sureda Riera et al., 2022) is a publicly available corpus hosted on Harvard Dataverse, comprising 907,814 HTTP requests spanning 13 multi-label CAPEC attack categories. It serves as the source corpus for this study.

### Derived Dataset: SRBH-335k-cleaned
A derived four-class dataset is constructed from the SR-BH 2020 corpus through a multi-stage cleaning pipeline producing approximately 335,821 unique samples distributed across four categories: SQL Injection, Normal, Other Attacks, and Code Injection. The derivation process involves:

1. **Canonicalization:** URL decoding, HTML entity decoding, Unicode normalization (NFKC), whitespace normalization, and null byte removal — applied non-destructively to preserve original payload case patterns relevant to obfuscation detection
2. **Category remapping:** The 13 original CAPEC categories are consolidated into four mutually exclusive classes using a deterministic priority-based mapping (SQL Injection → Code Injection → Other Attacks → Normal)
3. **Exact deduplication:** SHA-256 hashing of canonicalized identity strings (method + request + body) removes exact duplicates prior to train/validation/test splitting to prevent data leakage
4. **Near-duplicate analysis:** MinHash/LSH-based similarity estimation on a 50,000-sample representative subsample at a 0.90 similarity threshold revealed a **39.23% near-duplicate rate** with an estimated 10,785 clusters in the sample (projected ~72,000 clusters dataset-wide). Near-duplicates are preserved to maintain attack obfuscation realism, but their prevalence motivates aggressive dropout (0.3–0.5), data augmentation, and careful overfitting monitoring during training. The imbalance ratio between the majority class (SQL Injection: 184,645) and minority class (Code Injection: 11,090) is **16.65:1**, classified as severe.
5. **Label noise quarantine:** Heuristic validation rules scan benign-labeled samples for suspicious attack indicators (SQL keywords, tautologies, script tags, command injection operators, path traversal patterns); flagged samples are isolated in a quarantine dataset rather than deleted, following the WAMM framework finding of ~10% benign mislabeling (Sanhour et al., 2025)
6. **Quality validation:** Manual inspection of quarantined samples and random per-class samples to verify heuristic precision

Final dataset statistics — including exact sample counts per class, total corpus size, and per-split distributions — are documented in the pipeline's audit log.

#### Class Distribution (Post-Cleaning)
| Class | Count | Percentage |
|-------|-------|------------|
| SQL Injection | ~184,645 | ~54.98% |
| Normal | ~125,698 | ~37.43% |
| Other Attacks | ~14,388+ | ~4.28%+ |
| Code Injection | ~11,090 | ~3.30% |

#### Imbalanced Dataset Training Strategy
The cleaned dataset retains its natural class distribution rather than being artificially balanced. This design choice reflects established practice in security ML systems, where models must learn to operate under production-realistic class priors. Class imbalance is addressed through:
- **Class-weighted loss:** `CrossEntropyLoss(weight=class_weights)` using inverse-frequency weighting to penalize minority-class misclassification proportionally
- **Focal loss (ablation):** Evaluated as an alternative imbalance-handling strategy
- **Evaluation via Macro F1:** Ensures per-class performance is not masked by majority-class dominance

#### Cleaning Pipeline Results (Empirical)
| Stage | Count | Notes |
|-------|-------|-------|
| Original dataset | 907,815 | Raw SR-BH 2020 corpus |
| After malformed removal | 907,813 | 2 rows missing HTTP method/request |
| After exact deduplication | 363,053 | 544,760 exact duplicates removed (60%) |
| After label noise quarantine | 335,821 | 27,232 suspicious benign samples quarantined |
| **Final cleaned dataset** | **335,821** | **37% retention rate** |

### Preprocessing Pipeline
The cleaning pipeline (`clean_907k.py`) implements the following stages:
1. **Loading and validation:** Verify required columns, detect corrupted rows
2. **Canonicalization:** URL decoding, HTML entity decoding, Unicode normalization (NFKC), whitespace collapse, null byte removal
3. **Malformed request removal:** Drop rows with missing HTTP method or request path
4. **Exact duplicate removal:** SHA-256 hash of canonicalized identity string; deterministic ordering
5. **Near-duplicate estimation:** MinHash/LSH similarity analysis on representative subsample
6. **Label noise quarantine:** Heuristic pattern matching on benign-labeled samples
7. **CAPEC label mapping:** Deterministic priority-based mapping to four thesis classes
8. **Stratified splitting:** 80/10/10 split stratified by final class labels
9. **Leakage verification:** Confirm zero identity-hash overlap across splits
10. **Tokenization:** Native tokenizer per backbone (e.g., WordPiece with 30,522 tokens)

### Payload Length Analysis and Sequence Length Selection
Payload length statistics are computed during preprocessing to justify `MAX_LEN`:
- Analysis of the cleaned dataset indicates that 95% of payloads fall below ~60 tokens, supporting `MAX_LEN = 128` as sufficient for most samples while maintaining CPU inference efficiency.
- A truncation ablation study will quantify the impact of truncation on detection performance.

### Pipeline Output Structure
```
data/processed/srbh_clean_v1/
├── cleaned_dataset.parquet       # Full cleaned dataset
├── train.parquet                 # Training split (80%)
├── val.parquet                   # Validation split (10%)
├── test.parquet                   # Test split (10%, held out)
├── quarantine_dataset.parquet    # Flagged suspicious benign samples
├── near_duplicate_report.json    # Similarity statistics
└── audit_log.json                # Stage counts, checksums, metadata
```

---

## MCDM Evaluation Framework

### Purpose
A Multi-Criteria Decision-Making (MCDM) framework is adopted to provide a structured, transparent, and reproducible method for selecting the best-performing model from among the three transformer candidates. The framework ensures that the final model selection accounts for multiple engineering and operational criteria rather than optimizing for a single metric.

### Criteria Definitions

| Criterion | Definition | Direction |
|-----------|------------|-----------|
| Classification Accuracy | Overall test-set accuracy on the SRBH-335k-cleaned dataset | Maximize |
| Macro F1-Score | Harmonic mean of precision and recall, averaged across all four classes | Maximize |
| Inference Latency | Time to classify a single HTTP request on the target deployment hardware | Minimize |
| Model Size | Total parameter count and disk footprint of the exported model | Minimize |
| Calibration Quality | Expected Calibration Error (ECE), computed using 10-bin reliability diagrams on the validation set prior to threshold application | Minimize |
| Out-of-Distribution Robustness | Performance retention under controlled perturbation experiments (see OOD Evaluation Protocol below) | Maximize |

### Weight Assignment Rationale

Criterion weights are informed by the MCDM-for-cybersecurity literature (Alhakami, 2024; Alharbi et al., 2021), which establishes that detection capability receives the highest priority in intrusion detection system evaluation:

| Criterion | Weight | Justification |
|-----------|--------|---------------|
| Classification Accuracy | 0.25 | Reflects the safety-critical nature of attack detection |
| Macro F1-Score | 0.20 | Captures per-class balance; critical for minority attack types |
| Inference Latency | 0.15 | Operational constraint for WAF integration |
| Model Size | 0.10 | Affects deployment feasibility on resource-constrained servers |
| Calibration Quality | 0.15 | Directly impacts confidence threshold reliability and enforcement precision |
| OOD Robustness | 0.15 | Addresses detection of novel/zero-day attack patterns |
| **Total** | **1.00** | |

### Normalization and Aggregation
- **Normalization:** Min–max normalization applied to raw criterion values to produce scores on a 0–10 scale
  - Maximize criteria: `Score = (value − min) / (max − min) × 10`
  - Minimize criteria: `Score = (max − value) / (max − min) × 10`
- **Aggregation:** Weighted linear combination of normalized scores

### Sensitivity Analysis
Criterion weights are normalized to sum to 1.0. Following Maliene et al. (2018), sensitivity analysis will evaluate ±5% perturbations to each weight independently to assess ranking stability under minor assumption shifts. This procedure is intended to verify that the selected model is robust to minor changes in weight assumptions (Muravskii et al., 2018).

**Role in system design:** The MCDM framework structures the model selection logic—it provides a transparent, reproducible method for ranking candidate models based on multiple operational criteria. The framework does not increase the runtime complexity of the deployed system; it is an evaluation methodology applied during the development phase to inform final model selection. The selected model is deployed as a standalone inference engine, independent of the MCDM ranking process.

### Operational Definition of Out-of-Distribution (OOD) Evaluation
Out-of-distribution robustness will be evaluated using controlled perturbation experiments rather than external datasets. Synthetic obfuscation techniques documented in the OWASP evasion taxonomy (e.g., URL encoding, case manipulation, comment injection, parameter pollution) will be applied to a subset of the held-out test data. OOD robustness will be operationalized as performance retention percentage relative to clean test-set performance:

> OOD Retention = (F1-score under perturbed conditions) / (F1-score under clean conditions)

This protocol ensures that OOD evaluation is reproducible and directly comparable across models.

### Data Population
Preliminary empirical results from PD1 training are now available (see Preliminary Model Comparison Results under Section 8). Overall accuracy, F1, ROC-AUC, and training time have been recorded for all three candidate architectures under identical experimental conditions. Remaining MCDM criteria — inference latency (ms/request on CPU), Expected Calibration Error (ECE), and OOD robustness retention — are pending experimental measurement. Full normalized rankings, weighted totals, and final model selection will be completed upon collection of all criterion values.

---

## Deployment & Automation

### Deployment Architecture
- Ubuntu Server with Nginx reverse proxy
- FastAPI application managed via systemd services
- PostgreSQL database for traffic logging, audit trails, and analyst feedback
- ModSecurity v3.0+ with OWASP CRS v4.x as the primary WAF layer
- SSL via Let's Encrypt for HTTPS connections

### Ansible Playbooks
Pre-written Ansible playbooks will automate the following infrastructure tasks:
- Initial system deployment (FastAPI, PostgreSQL, Nginx, ModSecurity)
- Temporary IP blocking/unblocking operations (time-bounded, auto-expiring)
- Rate-limiting adjustments
- Service restarts and configuration changes

All playbook-triggered actions are reversible and time-bounded. No Ansible playbook modifies CRS rules, ModSecurity configuration files, or permanent firewall policies.

### Python Orchestration Layer
The FastAPI backend implements an orchestration layer that:
- Loads the trained PyTorch model for inference
- Classifies incoming HTTP requests
- Triggers appropriate Ansible playbooks based on confidence level (e.g., HIGH confidence attack triggers temporary IP block playbook)
- Logs all automated actions with full audit trail (timestamp, source IP, confidence score, action taken, expiration time)

### Installation Documentation
Deployment documentation will be prepared for the target client (DICT), including environment setup, configuration, and operational procedures.

---

## Retraining Pipeline

A 20-day automated retraining pipeline addresses model drift and aims to maintain ongoing adaptation to evolving attack patterns:

1. **Daily collection:** Analyst-labeled samples collected at 02:00 from production traffic
2. **Trigger condition:** Full model fine-tuning triggered every 20 days upon accumulation of sufficient labeled samples (target: 500+)
3. **Fine-tuning:** The existing production model is fine-tuned (not retrained from scratch)
4. **Deployment gate:** A new model is deployed only if it demonstrates statistically significant improvement over the current production model on a held-out validation set derived from recent labeled samples. The comparison will use appropriate statistical tests (e.g., McNemar's test) to ensure observed differences are not due to random variation.
5. **Versioning:** Timestamp-based model naming with rollback capability
6. **Monitoring:** Performance metrics tracked per model version

### 20-Day Cycle Rationale
1. **Sample accumulation:** Estimated minimum 500 analyst-labeled samples needed for meaningful fine-tuning; at ~25 labels/day (conservative), 20 days provides sufficient data
2. **Model drift risk:** Studies show ML models can degrade 10–35% in accuracy over 6 months without retraining (Vela et al., 2022); 20-day cycles mitigate drift while allowing sufficient data collection
3. **Operational balance:** More frequent retraining (e.g., daily) risks overfitting to recent traffic patterns; less frequent (e.g., monthly) risks performance degradation

Retraining will be triggered only if the minimum labeled-sample threshold is met. If insufficient analyst feedback is accumulated within the 20-day window, the retraining cycle will extend automatically until the threshold is satisfied. This prevents underpowered fine-tuning and mitigates overfitting to limited recent samples.

This is further supported by security-specific research demonstrating that ML-based intrusion detection systems experience concept drift within days to weeks as attack patterns evolve, necessitating continuous adaptation strategies rather than static deployment (Kuppa & Le-Khac, 2022).

---

## Testing & Evaluation

### Unit Testing
- Preprocessing functions (URL decoding, tokenization, padding)
- Model prediction pipeline (input → inference → confidence classification)
- API endpoint correctness (request/response format, error handling)

### Integration Testing
- End-to-end classification workflow: HTTP request → ModSecurity log → ML inference → confidence tier → mitigation action
- Database logging integrity and audit trail completeness
- Analyst feedback loop validation
- Automation safeguard verification (time-bounded expiration, rollback capability)

### Security Testing
- Real attack payloads sourced from OWASP and PayloadsAllTheThings repositories
- Evasion technique testing (URL encoding, comment injection, case manipulation)
- False positive assessment using benign traffic samples

### Performance Validation
- Inference latency profiling under load
- End-to-end pipeline latency measurement (ModSecurity parsing → ML inference → database logging → response orchestration)
- Database query optimization verification

While isolated transformer inference can achieve low latency under optimized conditions, total end-to-end pipeline latency will be measured empirically during system testing. No deterministic latency guarantee is assumed prior to profiling under simulated traffic load.

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Dataset quality issues | High | High | Apply heuristic validation to flag suspicious benign samples; use MinHash/LSH deduplication; document all relabeling decisions with version control per WAMM framework; note that cited benchmarks are from uncleaned data |
| Model overfitting | Medium | High | Use dropout (0.3–0.5), early stopping (patience=5), learning rate scheduling; monitor train/val loss curves |
| Classification performance below expectations | Medium | Medium | Conduct hyperparameter tuning, evaluate alternative learning rate schedules, and analyze per-class failure modes; accept empirically achievable performance within the bounds of the dataset |
| False-positive enforcement | Medium | High | Confidence-gated mitigation is designed to limit aggressive enforcement to HIGH-confidence detections only; all blocks are temporary and auto-expiring; CRS-only baseline comparison quantifies net FP reduction |
| CRS and ML disagreement causing inconsistent mitigation | Medium | Medium | CRS detection is preserved as the primary detection engine; ML only gates enforcement intensity, not detection validity. All CRS-flagged requests are logged regardless of ML confidence tier. The hybrid enforcement hierarchy is designed to preserve CRS detection as the authoritative layer. |
| LLM API rate limits | Medium | Low | Implement request queueing; cache explanations for similar payloads; use free tier efficiently |
| LLM explanation quality | Medium | Low | Fallback to template-based explanations using attack class and confidence level; LLM treated as non-critical stretch goal |
| Integration failures | Medium | High | Modular architecture with defined interfaces; unit tests per module; staging environment before production |
| Pipeline latency exceeds operational requirements | Low | Medium | Model inference latency is expected to be low with ONNX Runtime optimization (Shen et al., 2022); end-to-end pipeline latency will be measured empirically under simulated traffic load; optimize database queries |
| Insufficient analyst labels for retraining | Medium | Medium | Retraining cycle extends automatically if label threshold not met; pipeline does not trigger underpowered fine-tuning |
| Timeline delays | Medium | Medium | Documentation produced incrementally per phase; LLM integration (Phase 5) is non-blocking and may be deferred; 2-week buffer in final phases; weekly progress checkpoints |
| Near-duplicate template bias in SR-BH | High | High | Many attack payloads repeat with tiny differences (templates), which can inflate test accuracy. Mitigation: MinHash/LSH near-duplicate analysis, cross-split leakage verification on identity hashes, and OOD evasion test set with obfuscated payloads |

---

## Project Timeline (36 Weeks)

| Phase | Weeks | Tasks | Owner | Documentation Deliverable |
|-------|-------|-------|-------|---------------------------|
| Phase 1: Data Preparation | 1–4 | Dataset acquisition, cleaning, EDA, preprocessing, DataLoader creation | Eugene | EDA report, data cleaning methodology |
| Phase 2: Model Development | 5–10 | Implement 3 transformer architectures, training, evaluation, MCDM-based selection, ablation study | Eugene | Model comparison report, ablation analysis |
| Phase 3: Backend Development | 11–16 | FastAPI endpoints, database, model integration, automation safeguards | Froilan | API documentation draft |
| Phase 4: Frontend Development | 17–22 | Dashboard UI, visualizations, admin controls | Mark, Junaid | UI mockups, user flow diagrams |
| Phase 5: LLM Integration | 23–26 | Attack explanation generation, rate limiting, PII sanitization (non-blocking; deferred as post-defense stretch goal if timeline is at risk) | Froilan, Eugene | LLM integration notes |
| Phase 6: ModSecurity Integration | 27–30 | WAF setup, log bridge, hybrid enforcement, CRS-only baseline evaluation | Froilan, Jabez | Integration guide draft |
| Phase 7: Ansible & Deployment | 31–34 | Playbooks, server setup, SSL, systemd services | Jabez | Deployment guide |
| Phase 8: Testing | 35–36 | Unit/integration tests, security testing, automation safeguard verification | Mark, Junaid | Test report |
| Phase 9: Documentation & Defense | 36–38 | Final documentation, user manual, presentation prep | All | Complete documentation package |

**Note:** Documentation is produced incrementally throughout each phase rather than compressed into final weeks. Phase 5 (LLM integration) is non-blocking and may be deferred without impacting the critical path.

### Critical Path
Data Preparation → Model Training → Backend Integration → ModSecurity Integration → Deployment

### Milestones
| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 4 | Data Ready | Cleaned dataset, DataLoaders |
| 10 | Model Selected | Trained models, MCDM comparison report, ablation study |
| 16 | Backend Complete | All API endpoints functional, automation safeguards implemented |
| 22 | Frontend Complete | Dashboard with visualizations and admin controls |
| 26 | LLM Integrated | Attack explanations working (or deferred) |
| 30 | WAF Integrated | Hybrid enforcement operational, CRS-only baseline measured |
| 34 | Deployed | System running on cloud server |
| 36 | Documentation Complete | Technical docs, user manual, presentation |

---

## Cost Estimate

| Item | Cost | Notes |
| ----- | ----- | ----- |
| Training Hardware | ₱0 | Team member laptops + free cloud (Google Colab, Kaggle) |
| Cloud VM Deployment (12 months) | ₱4,000–5,000 | DigitalOcean/AWS t3.medium equivalent |
| Domain Name (optional) | ₱500–800 | .com or .ph domain |
| SSL Certificate | ₱0 | Let's Encrypt (free) |
| LLM API (Groq/Phi-3) | ₱500–1,000 | Free tier sufficient for development; minimal cost for production |
| Contingency Fund | ₱1,500–2,000 | Unexpected expenses |
| **Total:** | **₱6,500–8,800** | |

---

## Hardware & Software Requirements

### Training Hardware
| Component | Requirement | Available Resource |
|-----------|-------------|-------------------|
| GPU | CUDA-capable GPU with ≥6GB VRAM | Team member laptops / Google Colab / Kaggle |
| RAM | 16GB minimum | Team member laptops |
| Storage | 10GB for dataset + models | Local SSD |

### Alternative Training Resources
- Google Colab (Free Tier): NVIDIA T4 GPU, 16GB VRAM
- Kaggle Kernels: P100/T4 GPU, 30 hours/week free

### Deployment Server Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8GB | 16GB |
| Storage | 50GB SSD | 100GB SSD |
| GPU | Not required | Optional for faster inference |

### Software Stack
| Component | Technology |
|-----------|------------|
| ML Framework | PyTorch 2.0+ |
| Transformers | Hugging Face Transformers, Optimum |
| Web Framework | FastAPI |
| Database | PostgreSQL |
| WAF | OWASP ModSecurity v3.0+, CRS v4.x |
| Deployment | Ansible, Docker |
| ONNX Runtime | For optimized CPU inference |

---

## Standards Alignment

### NIST SP 800-94 Rev. 1 — Guide to Intrusion Detection and Prevention Systems

This standard provides guidelines for selecting, implementing, and managing intrusion detection and prevention systems (IDPS). The proposed system aligns with NIST SP 800-94 recommendations for anomaly-based detection by implementing ML-enhanced analysis to complement signature-based WAF rules. The confidence classification mechanism (LOW/MEDIUM/HIGH) follows the standard's guidance on alert prioritization and response automation, reducing alert fatigue while maintaining security posture.

### OWASP CRS v4.x — Core Rule Set for ModSecurity

OWASP CRS provides a set of generic attack detection rules for web applications, serving as the foundation for ModSecurity deployments. The proposed system integrates with CRS v4.x as the primary WAF layer, with the ML model providing secondary confidence scoring for CRS-flagged alerts. This hybrid approach addresses CRS's known limitation of high false positive rates at elevated paranoia levels by gating enforcement intensity through ML-based confidence assessment. Critically, the ML layer does not override or modify CRS detection rules; it modulates the downstream mitigation response.

### ISO/IEC 27035-1:2023 — Information Security Incident Management

This international standard establishes principles and processes for information security incident management. The system's 20-day retraining pipeline and analyst feedback mechanism align with ISO/IEC 27035-1's requirements for continuous improvement of security controls. The automated response actions (rate limiting, temporary IP blocking) follow the standard's phased approach: detection, reporting, assessment, and response, with human review capabilities and full audit logging for all automated enforcement actions.

---

## References

Open Web Application Security Project. (2025). *A05: Injection.* In OWASP Top 10:2025. https://owasp.org/Top10/2025/A05_2025-Injection/

National Vulnerability Database. (2025). *CVE Statistics.* NIST. https://nvd.nist.gov/

Help Net Security. (2023, July 20). *67% of daily security alerts overwhelm SOC analysts.* https://www.helpnetsecurity.com/2023/07/20/soc-analysts-tools-effectiveness/

Narváez, A. R., et al. (2025). *Evaluation framework for false positives in open-source WAFs based on OWASP CRS paranoia levels.* Engineering Proceedings, 115(1), 1. https://www.mdpi.com/2673-4591/115/1/1

Scano, C., et al. (2024). *ModSec-Learn: Boosting ModSecurity with machine learning.* arXiv. https://arxiv.org/abs/2406.13547

OWASP Foundation. (2024). *OWASP ModSecurity Core Rule Set (CRS) documentation.* https://coreruleset.org/docs/

Wazuh, Inc. (2025). *Wazuh SIEM platform documentation.* https://wazuh.com/platform/siem/

Sanhour, B. H., et al. (2025). *Enhanced Web Payload Classification Using WAMM: An AI-Based Framework for Dataset Refinement and Model Evaluation.* arXiv. https://arxiv.org/abs/2512.23610

Zhang, X., et al. (2026). *Dual-channel Web Attack Detection Based on BERT Models (WADBERT).* arXiv. https://arxiv.org/abs/2601.21893

Sanhour, B. H., et al. (2025). *ML-based Intelligent Threat Identification for Phishing and SQL Injection Attacks.* IEEE. https://ieeexplore.ieee.org/document/11308233/

Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). *DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter.* arXiv preprint arXiv:1910.01108. https://arxiv.org/abs/1910.01108

Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)*, 4171–4186. https://doi.org/10.18653/v1/N19-1423

Seyyar, Y. E., Yavuz, A. G., & Ünver, H. M. (2021). An attack detection framework based on BERT and deep learning. *IEEE Access*, 9, 154235–154247. https://doi.org/10.1109/ACCESS.2021.3078315

Su, M.-Y., & Su, K.-L. (2023). BERT-based approaches to identifying malicious URLs. *Sensors*, *23*(20), 8499. https://doi.org/10.3390/s23208499

Wang, J., Li, Y., Zhou, Y., Li, S., & Ma, J. (2024). BSTFNet: An encrypted malicious traffic classification method based on BERT, TextCNN, and BiGRU. *Computers, Materials & Continua*, *78*(3). https://www.techscience.com/cmc/v78n3/55933/html

Lan, Z., Chen, M., Goodman, S., Gimpel, K., Sharma, P., & Soricut, R. (2020). *ALBERT: A Lite BERT for Self-supervised Learning of Language Representations.* International Conference on Learning Representations (ICLR). https://arxiv.org/abs/1909.11942

Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., & Zhou, M. (2020). *MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers.* Advances in Neural Information Processing Systems (NeurIPS), 33. https://arxiv.org/abs/2002.10957

Zhou, L., Yau, W.-C., Gan, Y. S., & Liong, S. T. (2025). *E-WebGuard: Enhanced neural architectures for precision web attack detection.* Computers & Security, 148, 104127. https://doi.org/10.1016/j.cose.2024.104127

Menaka, S. R., Dharani, G., Kalaivani, P., Basha, S. R., Hareeth, S. K. S., & Kalaiyarasan, V. (2025). An Efficient SQL Injection Detection with a Hybrid CNN & Random Forest Approach. *Journal of Information Systems Engineering and Management*, 10(18s). https://doi.org/10.52783/jisem.v10i18s.2979

Dong, T., & Cam, N. T. (2024). uitSQLid: SQL Injection Detection Using Multi Deep Learning Models Approach. *2024 International Conference on Information Management and Technology (ICIMTech)*, 1-6. https://doi.org/10.1109/ICIMTech63123.2024.10780813

Farhan, H. A. (2025). Robust and Accurate Phishing Detection Using Enhanced DistilBERT: A Transformer-Based Approach. *Journal of Al-Qadisiyah for Computer Science and Mathematics*, 17(3), 230-246. https://doi.org/10.29304/jqcsm.2025.17.32403

Liu, Y., & Dai, Y. (2024). Deep Learning in Cybersecurity: A Hybrid BERT–LSTM Network for SQL Injection Attack Detection. *IET Information Security*, 2024, 5565950. https://doi.org/10.1049/2024/5565950

Vela, D., Sharp, A., Zhang, R., et al. (2022). Temporal quality degradation in AI models. *Scientific Reports*, 12, 11685. https://doi.org/10.1038/s41598-022-15245-z

Hendrycks, D., Liu, Z., Wallace, A., Dziedzic, A., Krishnan, R., & Song, D. (2020). Pretrained Transformers Improve Out-of-Distribution Robustness. *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics (ACL)*, 2744-2754. https://doi.org/10.18653/v1/2020.acl-main.244

Alhakami, H. (2024). Evaluating modern intrusion detection methods in the face of Gen V multi-vector attacks with fuzzy AHP-TOPSIS. *PLoS ONE*, 19(6), e0302559. https://doi.org/10.1371/journal.pone.0302559

Alharbi, F., Hmida, F. B., & Cruz, R. (2021). Analyzing the Impact of Cyber Security Related Attributes for Intrusion Detection Systems. *Sustainability*, 13(22), 12337. https://doi.org/10.3390/su132212337

Amazon Web Services. (2024). Best practices for using the CAPTCHA and Challenge actions. AWS Documentation. https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-and-challenge-best-practices.html

Maliene, V., Dixon-Gough, R., & Malys, N. (2018). Dispersion of relative importance values contributes to the ranking uncertainty: sensitivity analysis of Multiple Criteria Decision-Making methods. *Applied Soft Computing*, 67, 286-298. https://doi.org/10.1016/j.asoc.2018.03.003

Muravskii, D., Mikhaylov, A., & Vasin, V. (2018). A sensitivity analysis in MCDM problems: A statistical approach. *Decision Making: Applications in Management and Engineering*, 1(2), 50-63. https://doi.org/10.31181/dmame1802050m

Cloudflare. (2024). Making WAF ML models go brrr: saving decades of processing time. *Cloudflare Engineering Blog*. https://blog.cloudflare.com/making-waf-ai-models-go-brr/

Chakir, O., & Sadqi, Y. (2023). Evaluation of open source web application firewalls for cyber threat intelligence. CRC Press. https://doi.org/10.1201/9781003373384-3

Gelman, B., Taoufiq, S., Vörös, T., & Berlin, K. (2023). That escalated quickly: An ML framework for alert prioritization. arXiv preprint arXiv:2302.06648. https://arxiv.org/abs/2302.06648

Ikramaputra, A., Sudarsono, A., & Ningsih, N. (2025). Enhancing web application firewall with ensemble machine learning to detect SQL injection attacks. 2025 International Electronics Symposium (IES), 521-526. https://doi.org/10.1109/IES67184.2025.11160726

Zhang, J., Li, S., Huang, W., Jing, H., et al. (2025). Design and computational modeling of an AI-based automated cybersecurity incident response system. IEEE Access. https://doi.org/10.1109/ACCESS.2025.3603975

Kuppa, A., & Le-Khac, N. A. (2022). Learn to adapt: Robust drift detection in security domain. Computers and Electrical Engineering, 103, 108239. https://doi.org/10.1016/j.compeleceng.2022.108239

OWASP Foundation. (2017). SQL injection bypassing WAF. OWASP. https://owasp.org/www-community/attacks/SQL_Injection_Bypassing_WAF

Shen, H., Zafrir, O., Dong, B., Meng, H., Ye, X., Wang, Z., Ding, Y., Chang, H., Boudoukh, G., & Wasserblat, M. (2022). Fast DistilBERT on CPUs. arXiv. https://arxiv.org/abs/2211.07715

Talpini, J., Sartori, F., & Savi, M. (2024). Enhancing trustworthiness in ML-based network intrusion detection with uncertainty quantification. arXiv preprint arXiv:2310.10655v2. https://arxiv.org/abs/2310.10655

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *Proceedings of the 34th International Conference on Machine Learning (ICML)*, 70, 1321–1330. https://proceedings.mlr.press/v70/guo17a.html

Xin, J., Tang, R., Lee, K., Yu, Y., & Lin, J. (2021). The art of abstention: Selective prediction and error regularization for natural language processing. *Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics (ACL)*, 1040–1051. https://doi.org/10.18653/v1/2021.acl-long.84

Canas, G., Nawara, T., & Krishnamurthy, V. (2021). *Classification with abstention but without disparities* [Preprint]. arXiv. https://arxiv.org/abs/2102.12258

Ioannou, A., Tussupov, J., Smits, I., & Mouratidis, H. (2023). A new AI-based semantic cyber intelligence agent. *Future Internet*, *15*(7), 231. https://doi.org/10.3390/fi15070231

Zhou, Y., Zhu, H., Chai, Y., Jiang, Y., & Liu, Y. (2024). *Towards trustworthy web attack detection: An uncertainty-aware ensemble deep kernel learning model* [Preprint]. arXiv. https://arxiv.org/abs/2410.07725

Yu, Y., Gomez-Cabello, C. A., Haider, S. A., Genovese, A., Prabha, S., Trabilsy, M., Collaco, B. G., Wood, N. G., Bagaria, S., Tao, C., & Forte, A. J. (2025). Enhancing clinician trust in AI diagnostics: A dynamic framework for confidence calibration and transparency. *Diagnostics*, 15(17), 2204. https://doi.org/10.3390/diagnostics15172204

Yang, L., Chen, Z., Wang, C., Zhang, Z., Booma, S., Cao, P., Adam, C., Withers, A., Kalbarczyk, Z., Iyer, R., & Wang, G. (2024). True Attacks, Attack Attempts, or Benign Triggers? An Empirical Measurement of Network Alerts in a Security Operations Center. *Proceedings of the 33rd USENIX Security Symposium*, 4089-4106. https://www.usenix.org/conference/usenixsecurity24/presentation/yang-limin

Sureda Riera, T., Bermejo Higuera, J., Bermejo Higuera, J. R., Martínez Herráiz, J. J., & Sicilia Montalvo, J. A. (2022). Prevention and Fighting against Web Attack through HTTP Traffic Analysis. *Sensors*, 22(7), 2676. https://doi.org/10.3390/s22072676

---