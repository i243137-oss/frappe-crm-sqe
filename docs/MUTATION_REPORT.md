# SE3002 SQE Project - Mutation Testing & CI Quality Gate Report

## 1. Executive Summary
This report presents the verification results for the **Mutation Testing and Continuous Integration (CI) Quality Gates** milestone on Frappe CRM.
- **Total Mutants Synthesized:** 16 targeted AST-level mutants across core business rules.
- **Mutants Killed:** 16 (100.0%)
- **Mutants Survived:** 0 (0.0%)
- **Final Mutation Score:** **100.0%**
- **Continuous Integration Pipeline:** Configured in `.github/workflows/sqe_quality_gate.yml` with automated quality gates enforcing unit, API, synthetic data generator, Playwright E2E, and mutation thresholds.

---

## 2. Mutation Analysis Matrix (16 Mutants)

| Mutant ID | Category / Target Rule | Code Mutation Description | Killing Test Suite | Status |
| :---: | :--- | :--- | :--- | :---: |
| `MUT-01` | **BR-01 Boundary** | Reject zero currency amount (`< 0` $\to$ `<= 0`) | `test_business_rules_and_boundaries.py` | **KILLED** |
| `MUT-02` | **BR-01 Boundary** | Invert currency boundary check (`< 0` $\to$ `> 0`) | `test_business_rules_and_boundaries.py` | **KILLED** |
| `MUT-03` | **BR-02 MCC Guard** | Invert Lost status verification (`== "Lost"` $\to$ `!= "Lost"`) | `test_deal_status_unit.py` | **KILLED** |
| `MUT-04` | **BR-02 MC/DC Pair B**| Invert mandatory reason check (`not reason` $\to$ `reason`) | `test_deal_status_unit.py` | **KILLED** |
| `MUT-05` | **BR-02 MC/DC Pair C**| Mutate logical compound decision (`and` $\to$ `or` on notes) | `test_deal_status_unit.py` | **KILLED** |
| `MUT-06` | **BR-02 MC/DC Pair D**| Mutate reason equality check (`== "Other"` $\to$ `!= "Other"`) | `test_deal_status_unit.py` | **KILLED** |
| `MUT-07` | **BR-03 Won Auto** | Replace automated `closed_date` with fixed stale date | `test_deal_status_unit.py` | **KILLED** |
| `MUT-08` | **BR-03 Won Auto** | Assign probability `0` instead of master default (100%) | `test_deal_status_unit.py` | **KILLED** |
| `MUT-09` | **BR-04 Gate** | Invert ineligible lead check on conversion (`== "Lost"`) | `test_lead_conversion_unit.py` | **KILLED** |
| `MUT-10` | **BR-04 Persistence** | Suppress lead conversion flag (`converted = 0`) | `test_lead_conversion_unit.py` | **KILLED** |
| `MUT-11` | **BR-04 Idempotency**| Invert policy check (`if_converted == "Fail"` $\to$ `!= "Fail"`) | `test_lead_conversion_unit.py` | **KILLED** |
| `MUT-12` | **BR-04 Idempotency**| Suppress return of existing deal (`return None`) | `test_lead_conversion_unit.py` | **KILLED** |
| `MUT-13` | **BR-01 Coverage** | Exclude `annual_revenue` from non-negative check | `test_business_rules_and_boundaries.py` | **KILLED** |
| `MUT-14` | **Audit Logging** | Suppress `add_status_change_log(self)` hook call | `test_status_audit_log_unit.py` | **KILLED** |
| `MUT-15` | **Shared Link** | Suppress primary contact creation during conversion | `test_lead_conversion_unit.py` | **KILLED** |
| `MUT-16` | **Shared Link** | Suppress foreign key assignment (`deal.lead = None`) | `test_lead_conversion_unit.py` | **KILLED** |

---

## 3. GitHub Actions CI Quality Gate Specification

File: `.github/workflows/sqe_quality_gate.yml`
```yaml
name: SQE Continuous Integration Quality Gate
on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  sqe-verification:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pytest pytest-cov playwright pytest-playwright pyyaml mutmut
      - run: playwright install --with-deps chromium
      - run: pytest tests/team/unit/test_infrastructure_smoke.py -v
      - run: pytest tests/team/unit/ -v --cov=crm --cov=tests/team --cov-branch --cov-fail-under=80
      - run: pytest tests/team/api/ -v
      - run: python tests/team/generator/data_generator.py && pytest tests/team/generator/ -v
      - run: pytest tests/team/e2e/test_crm_use_cases_playwright.py -v
      - run: python tests/team/mutation/mutation_runner.py
```

---

## 4. Summary & Verification Outcome
- **Mutation Engine:** Dedicated AST-level runner in [`tests/team/mutation/mutation_runner.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/mutation/mutation_runner.py)
- **Score:** 16 / 16 mutants killed (**100% Mutation Score**).
- **CI Configuration:** `.github/workflows/sqe_quality_gate.yml`
