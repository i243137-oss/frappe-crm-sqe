# SE3002 Software Quality Engineering – Project Progress Log
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/WEEKLY_PROGRESS.md`  

---

## Progress Overview

| Milestone / Deliverable | Status | Primary Focus & Verification Artifacts |
| :--- | :---: | :--- |
| **System Architecture & Workflow Discovery** | Completed | Upstream codebase analysis (`commit 678ed0d`), endpoint identification, DocType schemas (`docs/PROJECT_ANALYSIS.md`). |
| **Requirements, Business Rules & Test Planning** | Completed | 9 functional requirements (`docs/REQUIREMENTS.md`), 4 business rules with MCC/MCDC (`docs/BUSINESS_RULES.md`), RBAC matrix (`docs/USER_ROLES.md`), test plan (`docs/TEST_PLAN.md`), risk register (`docs/RISK_REGISTER.md`), RTM (`docs/TRACEABILITY_MATRIX.md`), test cases (`docs/TEST_CASES.md`). |
| **Test Infrastructure & Synthetic Data** | Completed | Pytest test harness (`tests/team/`), mock runtime environment (`tests/team/fixtures/mock_frappe.py`), synthetic factories (`lead_factory.py`, `deal_factory.py`), JSON test data (`synthetic_leads.json`, `synthetic_deals.json`, `bva_test_data.json`), smoke verification suite passing 6/6 tests with coverage reporting. |
| **White-Box Unit Testing & Coverage** | Completed | 56/56 unit tests passing (100%), 100% statement and branch coverage on business logic, complete 10-row MCC suite and 4 MC/DC independence pairs for BR-02, 3-point BVA for BR-01 (`docs/UNIT_TEST_REPORT.md`). |
| **API & Integration Testing** | Completed | 24 API tests covering `POST /api/method/...convert_to_deal`, `PUT /api/resource/CRM Deal/{name}`, `GET` endpoints, RPC `set_value`, 3-point BVA, EP, RBAC checks, and cross-workflow pipeline (`docs/API_TEST_REPORT.md`). |
| **OpenAPI Test Data Generator** | Completed | OpenAPI 3.0 specification (`docs/openapi_crm.yaml`), automated BVA/EP generator (`tests/team/generator/data_generator.py`), synthetic test bank (`tests/team/data/generated_api_payloads.json`), and validator suite (`docs/DATA_GENERATOR_REPORT.md`). |
| **Playwright Use Case Automation** | Pending | Target: Browser end-to-end automation of happy path, alternative flows, and exception flows. |
| **Mutation Testing & CI Quality Gates** | Pending | Target: Mutation score measurement, killing mutants, and GitHub Actions quality gate. |
| **Static Analysis & Cyclomatic Complexity** | Pending | Target: SonarQube analysis and manual CFG complexity calculation. |
| **Usability & Accessibility Audits** | Pending | Target: axe-core and Lighthouse automated audits with before-and-after reports. |
| **Defensive Security Assessment** | Pending | Target: RBAC enforcement validation, session cookie inspection, and dependency audit. |
| **Performance & Recovery Testing** | Pending | Target: k6 OSS load testing (1 VU & 5 VUs) and controlled fault recovery validation. |
| **Defect Management & Completion Report** | Pending | Target: 5 Whys, Fishbone, Pareto defect analysis, and final completion report. |
