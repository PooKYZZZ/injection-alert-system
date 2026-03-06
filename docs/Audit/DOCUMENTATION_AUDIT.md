# Documentation Audit — Injection Alert System

**Audit Date:** 2026-02-23  
**Auditor Role:** Senior Technical Architect  
**Scope:** All `.md` files in `PDDDD/`  
**Master Document:** `plans/combined.md`  
**Authoritative Boundary:** `plans/pd1_pd2_boundary_statement.md` (PD1 = Objectives 1–2 only)

---

## DOCUMENT AUDIT TABLE

| # | Filename | Location | Decision | Reason (max 12 words) | Action |
|---|----------|----------|----------|-----------------------|--------|
| 1 | `combined.md` | `plans/` | **KEEP** | Master document; single source of truth | No action needed |
| 2 | `walkthrough.md` | `plans/` | **ARCHIVE** | Source doc fully synthesized into combined.md | Move to `docs/archive/walkthrough.md` — reason: superseded by combined.md |
| 3 | `architecture_review.md` | `plans/` | **ARCHIVE** | Source doc fully synthesized into combined.md | Move to `docs/archive/architecture_review.md` — reason: superseded by combined.md |
| 4 | `BUILD_GUIDE.md` | root | **KEEP** | Phase-by-phase build checklist; developer-facing, unique content | No action needed |
| 5 | `CONTEXT.md` | root | **KEEP** | Quick-reference project context; update PD1 boundary to Obj 1–2 | Fix PD1/PD2 boundary (line 123): change "1-3" → "1-2" per boundary statement |
| 6 | `notion_ai_prompt.md` | root | **DELETE** | Internal AI prompt; not a project doc; zero audience value | Delete — content is internal tooling, not referenced, fully covered by checklists |
| 7 | `README.md` | `checklists/` | **KEEP** | Index page for all 9 checklists; fix hyphen paths | Fix `ml-model/` → `ml_model/` and `web-app/` → `web_app/` on lines 74, 77, 80 |
| 8 | `01_PROJECT_SETUP.md` | `checklists/` | **KEEP** | Setup checklist; fix hyphen paths and PD1 boundary | Fix `ml-model/` → `ml_model/`, `web-app/` → `web_app/` (L28–30); fix PD1 scope to Obj 1–2 |
| 9 | `02_DATA_PREPARATION.md` | `checklists/` | **KEEP** | Data prep checklist; active for PD1 Objective 1 | No action needed |
| 10 | `03_ML_MODEL.md` | `checklists/` | **KEEP** | Model dev checklist; active for PD1 Objective 2 | No action needed |
| 11 | `04_WEB_APP.md` | `checklists/` | **KEEP** | Web app checklist; mark as PD2 scope per boundary | Add note: "PD2 scope — deferred per pd1_pd2_boundary_statement.md" |
| 12 | `05_RETRAINING.md` | `checklists/` | **KEEP** | Retraining checklist; mark as PD2 scope | Add note: "PD2 scope" |
| 13 | `06_MODSECURITY.md` | `checklists/` | **KEEP** | ModSecurity checklist; mark as PD2 scope | Add note: "PD2 scope" |
| 14 | `07_ANSIBLE.md` | `checklists/` | **KEEP** | Ansible checklist; mark as PD2 scope | Add note: "PD2 scope" |
| 15 | `08_TESTING.md` | `checklists/` | **KEEP** | Testing checklist; spans PD1+PD2 | No action needed |
| 16 | `09_DOCUMENTATION.md` | `checklists/` | **KEEP** | Documentation checklist; spans PD1+PD2 | No action needed |
| 17 | `conceptual_framework.md` | `plans/` | **KEEP** | Academic framework with Mermaid diagram; Chapter 2 input | No action needed |
| 18 | `pd1_data_flow.md` | `plans/` | **KEEP** | PD1 data pipeline diagram; unique implementation blueprint | No action needed |
| 19 | `pd1_pd2_boundary_statement.md` | `plans/` | **KEEP** | Authoritative boundary doc; PD1 = Obj 1–2 only | No action needed |
| 20 | `definition_of_terms.md` | `plans/` | **KEEP** | Glossary for Chapters 1–3; panel reviewer reference | No action needed |
| 21 | `reference_clusters.md` | `plans/` | **KEEP** | Literature review clusters for Chapter 2 synthesis | No action needed |
| 22 | `model_hyperparameter_tables.md` | `plans/` | **KEEP** | Complete model specs with code snippets; ML dev reference | No action needed |
| 23 | `modsecurity_crs_baseline_comparison_plan.md` | `plans/` | **KEEP** | Baseline comparison methodology; Chapter 3 input | No action needed |
| 24 | `research_design_statement.md` | `plans/` | **KEEP** | Chapter 3 methodology opening; unique academic content | No action needed |
| 25 | `scope_and_limitations.md` | `plans/` | **KEEP** | Chapter 1 scope section; unique academic content | No action needed |
| 26 | `(TEAM 13) CPEQC 029 Design Project (Chapter 1 & 3).md` | root | **KEEP** | Feasibility report; official submission document | Rename to `feasibility_report.md` for path safety (ampersand + spaces) |
| 27 | `waf_injection_detection_model_comparison.md` | `WAF Model Research/` | **KEEP** | Deep model research with 50+ citations; unique content | Rename folder `WAF Model Research/` → `waf_model_research/` (underscore convention) |
| 28 | `Final-Project Design Paper_Team 8 - Chapter 1-5.md` | `REFERENCES/` | **ARCHIVE** | External reference paper from another team; not project doc | Move to `docs/archive/team8_reference_paper.md` — reason: external reference only |
| 29 | `Template chapter 1-3.md` | `REFERENCES/` | **ARCHIVE** | Template file; no original content; scaffold only | Move to `docs/archive/template_chapter_1-3.md` — reason: template scaffold |
| 30 | `PLANNING_DOCUMENT.md` | `REFERENCES/output/` | **KEEP** | Paper planning doc; active writing guide for all chapters | No action needed |
| 31 | `Chapter1_Project_Background.md` | `REFERENCES/output/` | **KEEP** | Completed Chapter 1 draft; active academic deliverable | No action needed |
| 32 | `Chapter2_Project_Design.md` | `REFERENCES/output/` | **KEEP** | Completed Chapter 2 draft; active academic deliverable | No action needed |
| 33 | `Chapter3_Design_Tradeoffs.md` | `REFERENCES/output/` | **KEEP** | Completed Chapter 3 draft; active academic deliverable | No action needed |
| 34 | `An Evidence-Based Blueprint...` | `citations/` | **ARCHIVE** | AI-generated synthesis doc; raw research, not audience-facing | Move to `docs/archive/citation_blueprint.md` — reason: raw AI research output |
| 35 | `Evaluation_of_Open_Web_Application_Firewalls...` | `citations/` | **ARCHIVE** | Raw citation notes; content absorbed into chapters | Move to `docs/archive/citation_waf_evaluation.md` — reason: raw research notes |
| 36 | `Research Gaps for WAF Confidence Classification.md` | `citations/` | **ARCHIVE** | Raw Perplexity output; research phase artifact | Move to `docs/archive/citation_research_gaps.md` — reason: raw AI research output |
| 37 | `You are a research assistant...` | `citations/` | **ARCHIVE** | Raw Perplexity prompt+output; internal research artifact | Move to `docs/archive/citation_confidence_threshold.md` — reason: raw AI prompt |
| 38 | `perplexity1.md` | `citations/` | **ARCHIVE** | Raw Perplexity output; gap-filling citations artifact | Move to `docs/archive/citation_perplexity1.md` — reason: raw AI research output |

---

## AUDIT SUMMARY

| Decision | Count | Files |
|----------|------:|-------|
| **KEEP** | 27 | Core docs, checklists, plans, academic chapters |
| **ARCHIVE** | 10 | Source docs, templates, raw citations, external refs |
| **DELETE** | 1 | `notion_ai_prompt.md` |
| **MERGE** | 0 | — |
| **NEEDS REVIEW** | 0 | — |

---

## POST-AUDIT ACTION LIST

### Do Immediately (< 30 min)

- `notion_ai_prompt.md`: **Delete** — internal AI prompt, not a project doc, content covered by checklists
- `CONTEXT.md` L123: **Fix** PD1 boundary from "1-3" to "1-2" per `pd1_pd2_boundary_statement.md`
- `checklists/README.md` L74, L77, L80: **Fix** `ml-model/` → `ml_model/` and `web-app/` → `web_app/`
- `checklists/01_PROJECT_SETUP.md` L28–30: **Fix** `ml-model/` → `ml_model/`, `web-app/` → `web_app/`; fix PD1 scope to Obj 1–2
- `walkthrough.md`: **Move** to `docs/archive/walkthrough.md`
- `architecture_review.md`: **Move** to `docs/archive/architecture_review.md`

### Do This Sprint (< 1 day)

- `(TEAM 13) CPEQC 029 Design Project (Chapter 1 & 3).md`: **Rename** to `feasibility_report.md` (remove special characters from filename)
- `WAF Model Research/` folder: **Rename** to `waf_model_research/` (underscore convention)
- `checklists/04_WEB_APP.md`, `05_RETRAINING.md`, `06_MODSECURITY.md`, `07_ANSIBLE.md`: **Add** PD2 scope banner per boundary statement
- `citations/` folder: **Move** all 5 files to `docs/archive/` with descriptive names (see table rows 34–38)
- `REFERENCES/Final-Project Design Paper_Team 8 - Chapter 1-5.md`: **Move** to `docs/archive/team8_reference_paper.md`
- `REFERENCES/Template chapter 1-3.md`: **Move** to `docs/archive/template_chapter_1-3.md`
- **Create** `docs/archive/` directory if it does not exist

### Defer to Later

- `CONTEXT.md`: Full refresh of "Files" section (L128–141) to reflect actual project structure after all renames/moves
- `checklists/README.md`: Update timeline table to align with boundary statement's 2-objective PD1 scope
- `combined.md`: Add cross-references to surviving plan docs (`conceptual_framework`, `pd1_data_flow`, etc.)

---

## SELF-CHECK

- [x] Every file has exactly ONE decision
- [x] Every MERGE row names the target file AND target section (N/A — no merges)
- [x] Every ARCHIVE row names the `/archive` destination
- [x] DELETE is only used when BOTH delete conditions are true
- [x] `combined.md` decision = KEEP
- [x] `walkthrough.md` and `architecture_review.md` decisions = ARCHIVE
- [x] Action list has entries grouped by effort
- [x] No prose outside the table and action list
