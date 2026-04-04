# Batch 7 Audit: Styling/assets/env-ignore/config drift

## 1. Batch summary

This batch contains one merge-blocking setup regression, one ignore-rule expansion that can hide source-adjacent generated artifacts, and a login-page branding refresh that mixes remediation work with asset churn. The most serious issue is `.env.example` now pointing `MODEL_PATH` and `MODEL_REGISTRY_PATH` at `web_app`, which contradicts the file's own comments, the staged model README, and the current setup docs. The asset side is noisy rather than dangerous: `w5.png` is used by the login page, `logo.png` is a shared brand asset used by the login page and sidebar, but `frontend/public/assets/login-left.svg` and `frontend/public/assets/network-connection-background-gradient_23-2148879893.png` appear to be dead additions with no repository references.

## 2. Files audited

- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\.env.example`
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\.gitignore`
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\assets\login-left.svg`
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\assets\network-connection-background-gradient_23-2148879893.png`
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\logo.png`
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\w5.png`

## 3. Findings

### Finding 1: `.env.example` now misstates the runtime model path and setup contract

- Severity: High
- Evidence:
  - `.env.example:15-19` tells operators to download the staged model into `ml_model/model_registry/staging/`, then sets both `MODEL_PATH` and `MODEL_REGISTRY_PATH` to `web_app`.
  - `ml_model/model_registry/staging/README.md:7-13` still instructs operators to extract the model under `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`.
  - `docs/SETUP.md:46-47` and `docs/SETUP.md:69` still document `MODEL_PATH=ml_model/models/mock_model.py` and `MODEL_REGISTRY_PATH=ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`.
  - `docs/architecture.md:62` and `docs/CONTEXT.md:52` state that `MODEL_REGISTRY_PATH` must point to an explicit model run directory.
  - `web_app/services/model_service.py:149-183` enforces explicit run-directory semantics in production and only recognizes a package directory when manifest/config-tokenizer files exist.
- Why this matters:
  - The example file now teaches an operator to point the app at `web_app`, which is source code, not the documented model artifact tree.
  - In local development this likely degrades into silent mock fallback, which hides a broken setup instead of surfacing it early.
  - In production-mode semantics it is actively misleading because `web_app` is not an explicit run directory.
- Audit conclusion:
  - This is config drift, not harmless cleanup. It increases setup confusion and masks whether the real model boundary is configured correctly.

### Finding 2: `.gitignore` adds source-adjacent ignore rules under `web_app/` without matching setup/documentation alignment

- Severity: Medium
- Evidence:
  - `.gitignore:126-134` now ignores `web_app/model.safetensors`, `web_app/tokenizer.json`, `web_app/tokenizer_config.json`, `web_app/config_used.json`, `web_app/eval_report.json`, `web_app/training_log.json`, `web_app/serving_manifest.json`, and `web_app/git_hash.txt`.
  - The packaging script in `ml_model/export/package_serving_artifact.py` packages artifacts into a staged run directory under `ml_model/model_registry/staging/`, not `web_app/`.
  - The same branch also repoints `.env.example` at `web_app`, creating the appearance that `web_app/` is now a valid runtime artifact location even though the docs and model service contract still describe `ml_model/model_registry/...` as the active boundary.
- Why this matters:
  - These ignore rules are narrow enough that they do not blanket-ignore the entire `web_app/` tree, which is better than a broad `web_app/*` rule.
  - But they still hide generated runtime artifacts if someone starts copying model files into the application source tree, and that behavior is not documented as the supported setup path.
  - In combination with the `.env.example` drift, this can conceal a locally invented deployment shape from review.
- Audit conclusion:
  - This is not an exposure bug by itself, but it materially increases the chance that risky source-adjacent artifact churn happens off-review.

### Finding 3: The login-page refresh mixes remediation with branding/media churn and includes dead assets

- Severity: Medium
- Evidence:
  - Commit `e574d19` introduces or changes `frontend/public/w5.png`, `frontend/public/logo.png`, `frontend/public/assets/login-left.svg`, and `frontend/public/assets/network-connection-background-gradient_23-2148879893.png` together with a login page redesign.
  - `frontend/app/(auth)/login/page.tsx:42-49` references `/w5.png` as a full-screen background.
  - `frontend/app/(auth)/login/page.tsx:66-73` and `frontend/components/layout/Sidebar.tsx:38` reference `/logo.png`.
  - Repository search found no references to `login-left.svg` or `network-connection-background-gradient_23-2148879893.png` anywhere in the worktree.
- Why this matters:
  - Two assets in scope are dead on arrival, which adds review noise and future cleanup burden.
  - The filename `network-connection-background-gradient_23-2148879893.png` is stock-asset style naming and is especially weak from a repository-discipline standpoint.
  - The login redesign replaced token-driven branding with raster-backed visuals without any visible connection to the functional remediation elsewhere in the batch.
- Audit conclusion:
  - This is unnecessary noise in a remediation branch. The issue is not visual taste; it is unscoped asset churn plus two unused files.

### Finding 4: `w5.png` is wired, but it is still heavyweight merge noise for a functional branch

- Severity: Low
- Evidence:
  - `frontend/public/w5.png` is a new 1,239,916-byte asset.
  - It is referenced only from `frontend/app/(auth)/login/page.tsx:42-49`.
- Why this matters:
  - The file is not dead, but it is large and only serves a cosmetic login-background role.
  - In a branch focused on remediation, a large binary addition with a generic filename increases review cost and conflict surface without addressing backend or BFF correctness.
- Audit conclusion:
  - The asset is functional for the login page, but it still reads as styling churn mixed into unrelated work.

## 4. High-risk files in this batch

- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\.env.example`
  - Misleads setup by pointing model env vars at `web_app` while the repo still documents and enforces `ml_model/model_registry/...` semantics.
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\.gitignore`
  - Newly hides generated model artifacts under `web_app/`, which can mask source-adjacent runtime artifact drift when combined with the `.env.example` change.
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\assets\login-left.svg`
  - Unused new asset; pure merge noise.
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\assets\network-connection-background-gradient_23-2148879893.png`
  - Unused new asset with low-discipline naming; pure merge noise.

## 5. Files that appear disciplined

- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\logo.png`
  - Although modified, it is a shared branding asset referenced by both the login page and the sidebar, so it is at least connected to real code paths.
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\frontend\public\w5.png`
  - Not dead; directly referenced by the login page. The concern is branch scope and size, not orphaning.
- `G:\AI\PDDDD\injection-alert-system\.worktrees\fix-bezzy-remediation\.gitignore`
  - The new ignore entries are targeted filenames rather than a blanket `web_app/*` ignore, which limits collateral masking even though the underlying direction is still questionable.

## 6. Questions or ambiguities needing cross-batch verification

- Is there any approved packaging or deployment flow, outside the scoped files, that intentionally copies serving artifacts into `web_app/` and expects runtime env vars to point there? Current docs and `ml_model/export/package_serving_artifact.py` do not show that flow.
- Was the `.env.example` repointing to `web_app` coordinated with any documentation update outside this batch? The current `docs/SETUP.md`, `docs/architecture.md`, `docs/CONTEXT.md`, and the staged model README all still say the active boundary is `ml_model/model_registry/...`.
- Was the login-page visual rewrite part of the actual remediation scope, or was unrelated styling merged into the same branch? The asset additions and the login redesign commit message do not justify the coupling.
- Is there any code outside the current search scope that references `frontend/public/assets/login-left.svg` or `frontend/public/assets/network-connection-background-gradient_23-2148879893.png` dynamically? No static repository references were found.

## 7. Batch verdict

Batch 7 is not clean. The `.env.example` change is a high-confidence config-drift regression that misstates the model setup boundary, and the `.gitignore` additions make that drift easier to hide. The asset portion is mostly merge noise: one shared logo update, one wired login background, and two dead assets with no code references. This batch should be treated as failing audit until the env-path story and the unused asset churn are explained or removed.
