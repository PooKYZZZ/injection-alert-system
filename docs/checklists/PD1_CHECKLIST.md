# PD1 Task Checklist — Team 13

**Objective:** Design and implement a deep learning-based injection alert triage system that detects and classifies web injection attacks with confidence-based automated response.

---

## Eugene — Data / ML

- [ ] Acquire SR-BH 2020 dataset from Harvard Dataverse
- [ ] Remap 13 CAPEC categories into 4 classes (Normal, SQL Injection, Code Injection, Other Attacks)
- [ ] Apply preprocessing: URL decoding, null byte removal, whitespace normalization
- [ ] Run MinHash/LSH deduplication to prevent data leakage
- [ ] Perform EDA (class distribution, payload length stats, sample inspection)
- [ ] Build stratified DataLoaders (80/10/10 split)
- [ ] Implement and train 3 hybrid architectures: BERT-base+CNN, DistilBERT+CNN, MiniLM-L6+CNN
- [ ] Evaluate models: accuracy, macro F1, FPR, confusion matrix
- [ ] Apply temperature scaling for confidence calibration
- [ ] Select best model using MCDM framework
- [ ] Export trained model and tokenizer

---

## Gayao — DevOps / Project Manager / Backend (Core Logic)

**DevOps & Infrastructure**
- [ ] Set up Ubuntu Server with Nginx reverse proxy
- [ ] Install and configure ModSecurity v3.0+ with OWASP CRS v4.x
- [ ] Build audit.log bridge to feed flagged requests to ML model
- [ ] Implement hybrid enforcement logic (CRS detects → ML scores → tier applied)
- [ ] Run CRS-only baseline evaluation at Paranoia Level 1 and 2
- [ ] Write Ansible playbook for initial system deployment
- [ ] Write Ansible playbook for temporary IP blocking/unblocking
- [ ] Configure systemd services for FastAPI and Nginx
- [ ] Set up SSL via Let's Encrypt

**Backend — Heavy Logic**
- [ ] Integrate trained ML model into the FastAPI prediction pipeline (load model, tokenizer, run inference)
- [ ] Implement confidence-gated response logic (LOW / MEDIUM / HIGH enforcement tiers)
- [ ] Implement automation safeguards (time-bounded blocks, audit logging, rollback capability)
- [ ] Implement `/api/feedback` endpoint (analyst label submission for retraining)

**Project Management**
- [ ] Coordinate integration between all modules (ML ↔ Backend ↔ Frontend ↔ DevOps)
- [ ] Track overall progress, resolve blockers, and ensure PD1 deliverables are on schedule

---

## Jabez — Backend (API & Database)

- [ ] Set up FastAPI project structure
- [ ] Implement `/api/predict` endpoint (single request classification)
- [ ] Implement `/api/alerts` endpoint (paginated alert history)
- [ ] Implement `/api/stats` endpoint (attack statistics)
- [ ] Set up PostgreSQL schema (timestamp, source_ip, http_request, prediction, confidence, confidence_level, action_taken)
- [ ] Write unit tests for all endpoints

---

## Junaid — Frontend & DevOps Support

- [ ] Design dashboard layout (wireframes / mockups)
- [ ] Build real-time attack feed table (source IP, class, confidence, action)
- [ ] Build confidence tier visual indicators (LOW / MEDIUM / HIGH)
- [ ] Build analyst labeling interface (approve / relabel predicted alerts)
- [ ] Build admin controls (manual unblock, threshold adjustment)
- [ ] Assist Jabez with server setup and Ansible testing

---

## Mark — Docs / Frontend Support

- [ ] Write API documentation (endpoint descriptions, request/response formats)
- [ ] Write user manual (dashboard usage, analyst workflow)
- [ ] Build attack statistics charts (bar/pie chart by class and confidence tier)
- [ ] Assist Junaid with frontend components
- [ ] Compile final PD1 documentation package
- [ ] Prepare presentation slides

---

## Shared

- [ ] Each member writes unit tests for their own module
- [ ] Code review at least one other member's module before PD1
