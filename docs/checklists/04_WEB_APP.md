# Web Application Checklist

> **PD2 scope — deferred per pd1_pd2_boundary_statement.md**

**Why This Matters:** The web application is the interface between your ML model and security analysts. It must be fast, reliable, and provide actionable information. A poorly designed interface leads to ignored alerts and missed threats.

---

## Backend Development (FastAPI)

### Project Setup
- [ ] Create FastAPI project structure
- [ ] Set up CORS middleware
- [ ] Configure environment variables
- [ ] Set up logging configuration

### API Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/predict` | POST | Classify single HTTP request | [ ] |
| `/api/batch-predict` | POST | Classify multiple requests (max 100) | [ ] |
| `/api/stats` | GET | Get attack statistics for charts | [ ] |
| `/api/alerts` | GET | Get recent alerts (paginated) | [ ] |
| `/api/alerts/{id}` | GET | Get specific alert details | [ ] |
| `/api/feedback` | POST | Submit analyst feedback | [ ] |
| `/api/health` | GET | System health check | [ ] |
| `/api/explain` | POST | LLM-based attack explanation (stretch) | [ ] |

### Model Integration
- [ ] Load PyTorch model at startup
- [ ] Load tokenizer/vocabulary
- [ ] Create preprocessing pipeline
- [ ] Create prediction function
- [ ] Implement confidence classification
- [ ] Handle model errors gracefully

### Database Integration
- [ ] Set up PostgreSQL connection
- [ ] Create database models (SQLAlchemy)
- [ ] Implement traffic_logs table:
  - id, timestamp, source_ip
  - http_method, http_path, http_query, http_body
  - user_agent, content_type
  - model_prediction, model_confidence, confidence_level
  - action_taken
  - analyst_label, labeled_at, labeled_by
- [ ] Implement alert storage
- [ ] Implement feedback storage

### Logging System
- [ ] Configure structured logging
- [ ] Log all predictions
- [ ] Log all actions taken
- [ ] Log errors and exceptions
- [ ] Create log rotation policy

---

## Frontend Development

### Dashboard Layout
- [ ] Design header (system status, alert count)
- [ ] Design sidebar navigation:
  - [ ] Dashboard
  - [ ] Alerts
  - [ ] Reports
  - [ ] Settings
- [ ] Design main area (real-time attack visualization)
- [ ] Design right panel (recent alerts list)
- [ ] Make responsive design

### CSS Framework
- [ ] Choose: Bootstrap 5 or Tailwind CSS
- [ ] Set up base styles
- [ ] Create component library
- [ ] Implement dark/light mode (optional)

### Key Pages
- [ ] Dashboard page (overview, charts)
- [ ] Alerts page (list, filtering, search)
- [ ] Alert detail page (full request, prediction, feedback)
- [ ] Reports page (statistics, trends)
- [ ] Settings page (thresholds, notifications)

### Real-time Updates
- [ ] Implement polling (simpler) OR
- [ ] Implement WebSockets (better for real-time)
- [ ] Update alert list in real-time
- [ ] Update statistics in real-time

### Visualizations
- [ ] Attack type distribution chart (pie/donut)
- [ ] Attack timeline chart (line)
- [ ] Confidence level breakdown (bar)
- [ ] Top attacking IPs (table)
- [ ] Recent alerts table

---

## Response Actions Implementation

### Low Confidence Actions (< 50%)
- [ ] Log the request for analysis
- [ ] Apply light rate limiting (100 req/min)
- [ ] Show captcha on subsequent requests
- [ ] Do NOT block the user

**Rationale:** Low confidence means the model is uncertain. Blocking legitimate users causes frustration. Rate limiting slows potential attackers without significantly impacting normal users.

### Medium Confidence Actions (50-80%)
- [ ] Log with elevated priority
- [ ] Apply aggressive rate limiting (20 req/min)
- [ ] Enforce captcha on every request
- [ ] Alert security team via dashboard

**Rationale:** Medium confidence indicates likely malicious intent. The user should be significantly slowed down while analysts investigate.

### High Confidence Actions (> 80%)
- [ ] Immediately block the request
- [ ] Block the IP address (temporary: 1 hour, extendable)
- [ ] Log to high-priority alert system
- [ ] Send notification to security team
- [ ] Add IP to firewall blocklist

**Rationale:** High confidence means the model is certain this is an attack. Immediate blocking prevents the attack from succeeding.

---

## LLM Integration (Stretch Goal - Per Chapter 1)

### API Endpoint
- [ ] Create POST `/api/explain` endpoint
- [ ] Accept list of attack IDs (max 100)
- [ ] Generate LLM-based explanations for each attack

### PII Sanitization
- [ ] Implement PII detection and removal before sending to LLM
- [ ] Remove IP addresses
- [ ] Remove email addresses
- [ ] Remove phone numbers
- [ ] Remove credit card numbers
- [ ] Implement template-based fallback if LLM unavailable

### Rate Limiting
- [ ] Limit explanations to 1-2 minutes between batches
- [ ] Add rate limit headers to responses
- [ ] Implement queue system for explanation requests

---

## Authentication & Authorization (Optional)

- [ ] Implement user authentication
- [ ] Implement role-based access control
- [ ] Admin: Full access
- [ ] Analyst: View alerts, submit feedback
- [ ] Viewer: Read-only access

---

## API Documentation

- [ ] Set up automatic OpenAPI/Swagger docs
- [ ] Document all endpoints
- [ ] Document request/response schemas
- [ ] Document error codes
