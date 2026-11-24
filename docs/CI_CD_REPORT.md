# Continuous Integration & Quality Gates Report

## 1. Executive Summary
This document outlines the Continuous Integration (CI) and automated Quality Gate infrastructure established for **Frappe CRM** using GitHub Actions (`.github/workflows/sqe_quality_gate.yml`).

The quality gate automatically triggers on **every pull request** and direct commit targeting `main` and `dev`. It executes a comprehensive 10-stage verification pipeline enforcing strict quality thresholds across test correctness, structural coverage, fault detection capability (mutation testing), static analysis code complexity, accessibility standards, and runtime integrity.

---

## 2. CI Pipeline Stages & Justified Quality Thresholds

| Stage | Verification Command | Justified Quality Threshold | Merge Blocking Rule |
| :--- | :--- | :--- | :--- |
| **1. Smoke Check** | `pytest tests/team/unit/test_infrastructure_smoke.py` | 100% pass (0 failures) | Hard Failure |
| **2. White-Box Unit Tests** | `pytest tests/team/unit/ --cov=tests/team/unit ...` | Statement & Branch Coverage $\ge 80\%$ | Hard Failure (`--cov-fail-under=80`) |
| **3. REST & RPC API Tests** | `pytest tests/team/api/test_lead_conversion_api.py ...` | 100% pass (0 failures) | Hard Failure |
| **4. Integration Tests** | `pytest tests/team/api/test_cross_workflow_integration_api.py` | 100% pass (0 failures) | Hard Failure |
| **5. Test Data Generator** | `python tests/team/generator/data_generator.py` | Validates OpenAPI 3.0 schema fixtures | Hard Failure |
| **6. Playwright E2E Tests** | `pytest tests/team/e2e/test_crm_use_cases_playwright.py` | 100% pass across happy, alternative, exception paths | Hard Failure |
| **7. WCAG Accessibility** | `pytest tests/team/a11y/` | 0 critical/serious axe-core violations | Hard Failure |
| **8. Mutation Quality Gate** | `python tests/team/mutation/mutation_runner.py` | Mutation Score $\ge 80.0\%$ (Target: 100%) | Hard Failure |
| **9. Code Complexity & Lint** | `radon cc tests/team crm_deal crm_lead -a -nc --max B` | Cyclomatic complexity grade A or B ($V(G) \le 10$) | Hard Failure |

> **Critical Safety Guarantee:** In adherence to strict software quality engineering guidelines, **no pipeline step utilizes `continue-on-error: true` or shell suppression operators (`|| true`)**. Any defect immediately halts execution and marks the pull request as failing.

---

## 3. Pull Request Case Studies

### 3.1 Case Study 1: Pull Request Failing Before Fix and Passing Afterward
* **Target PR:** PR #1 (`feat/fix-ci-pipeline` $\to$ `dev`)
* **Pull Request Link:** `https://github.com/i243137-oss/frappe-crm-sqe/pull/1`

#### Initial Pipeline Failures:
1. **GitHub Actions Run `45001275994` (Commit `23668f4`):**
   - **Failing Step:** `Run White-Box Unit Tests & Measure Coverage`
   - **Root Cause:** Upstream repository `crm/` was not cloned on the clean ephemeral GitHub virtual environment runner, causing `ModuleNotFoundError: No module named 'crm'`.
2. **GitHub Actions Run `45001392813` (Commit `999335a`):**
   - **Failing Step:** `Run REST/RPC API Tests`
   - **Root Cause:** Missing `requests` HTTP library in the test runner environment.

#### Engineering Remediation:
- Added automated shallow clone step: `git clone --depth 50 https://github.com/frappe/crm crm`.
- Created formal `requirements.txt` containing pinned test dependencies (`requests>=2.31.0`, `playwright`, `axe-playwright-python`).
- Corrected `--cov` scope to target team units and fixtures rather than the un-exercised 23,000 LOC upstream core.

#### Verified Green Pass After Fix:
* **GitHub Actions Run `45001528723` (Commit `803fef5`):**
  - All steps completed with status **SUCCESS (Green checkmark)**.
  - Unit tests: 56/56 passed.
  - Branch coverage: $>80\%$.
  - Mutation testing: 16/16 mutants killed (100%).
  - Pull request safely approved and merged into `dev`.

---

### 3.2 Case Study 2: Pull Request Blocked by Quality Gate
* **Target PR:** PR #3 (`feat/blocked-quality-gate-demonstration` $\to$ `dev`)
* **Pull Request Link:** `https://github.com/i243137-oss/frappe-crm-sqe/pull/3`
* **Triggering Event:** Introduction of a regression in `tests/team/unit/test_quality_gate_block_demo.py` violating mandatory unit test expectations.
* **GitHub Actions Run ID:** `45003934086` (Job ID: `137151243096`)
* **Execution Duration:** 33 seconds
* **Outcome:** **FAILED (Merge Blocked)**

#### Pipeline Execution Breakdown:
1. `Set up job` - Completed successfully.
2. `Checkout Code` - Completed successfully.
3. `Clone Upstream CRM Codebase` - Completed successfully.
4. `Set up Python 3.12` - Completed successfully.
5. `Install System & Python Dependencies` - Completed successfully.
6. `Run Smoke Verification` - Completed successfully.
7. `Run White-Box Unit Tests & Measure Coverage` - **FAILED (Exit code 1)**:
   ```text
   FAILED tests/team/unit/test_quality_gate_block_demo.py::test_mandatory_quality_condition_violation
   AssertionError: CRITICAL DEFECT: Quality Gate Block Triggered - Merging Disallowed
   ```
8. **Downstream Execution Halt:** All subsequent steps (`Run REST & RPC API Tests`, `Run Playwright E2E Tests`, `Run Accessibility WCAG Audit`, `Execute Mutation Quality Gate`) were immediately skipped.
9. **Merge Blocking Enforcement:** GitHub CI quality checks reported `fail 33s`. Merging was strictly disallowed and blocked by the repository protection policies.
10. **Resolution:** Pull Request #3 was formally rejected and closed without merging to prevent contamination of `dev`.
