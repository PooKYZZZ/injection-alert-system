# Python 3.14 and Latest Stable Dependency Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the repository to Python 3.14 and refresh dependency pins to the latest stable releases that still support the repo's runtime and test surface.

**Architecture:** Keep package/version changes in the existing manifests and lockfiles, update CI and local setup instructions to prefer Python 3.14, and preserve current application contracts. Use the smallest set of dependency bumps that keeps install and tests green, then verify each boundary end-to-end.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, NumPy, PyTorch, Next.js, npm, GitHub Actions

---

### Task 1: Inventory current version surfaces

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements.train.txt`
- Modify: `pyproject.toml`
- Modify: `frontend/package.json`
- Modify: `package.json`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/SETUP.md`
- Modify: `README.md`

- [ ] **Step 1: Capture current pins and Python targets**
- [ ] **Step 2: Confirm latest stable releases that support Python 3.14**
- [ ] **Step 3: Record the files that must change**

### Task 2: Refresh backend runtime and CI to Python 3.14

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/SETUP.md`
- Modify: `README.md`

- [ ] **Step 1: Update backend dependency pins to latest 3.14-compatible releases**
- [ ] **Step 2: Update `requires-python` and formatter target version**
- [ ] **Step 3: Update CI to run backend on Python 3.14**
- [ ] **Step 4: Update setup docs to use Python 3.14**
- [ ] **Step 5: Regenerate or refresh backend lock/state if present**

### Task 3: Refresh frontend dependencies to latest stable releases

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `package.json`

- [ ] **Step 1: Bump frontend dependencies to latest stable compatible releases**
- [ ] **Step 2: Regenerate lockfiles**
- [ ] **Step 3: Verify the root `package.json` stays aligned with the frontend package**

### Task 4: Verify end-to-end compatibility

**Files:**
- Test: `requirements.txt`
- Test: `.github/workflows/ci.yml`
- Test: `frontend/package.json`

- [ ] **Step 1: Create a Python 3.14 environment and install backend deps**
- [ ] **Step 2: Run backend tests under Python 3.14**
- [ ] **Step 3: Run frontend typecheck and Vitest**
- [ ] **Step 4: Fix only compatibility breakages introduced by the upgrade**
- [ ] **Step 5: Re-run the affected verification commands**
