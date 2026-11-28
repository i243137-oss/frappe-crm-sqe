# SE3002 Software Quality Engineering – Risk Register & Mitigation Strategy
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/RISK_REGISTER.md`  
**Milestone:** SQE Core Deliverable  

---

## 1. Risk Assessment Framework

Risks are evaluated using a standard 5x5 quantitative matrix:
$$\text{Risk Score (RS)} = \text{Likelihood (L: 1–5)} \times \text{Impact (I: 1–5)}$$

* **High Risk (Red):** $15 \le \text{RS} \le 25$ (Immediate mitigation & rigorous testing mandatory).
* **Medium Risk (Yellow):** $8 \le \text{RS} \le 14$ (Monitored with targeted test cases).
* **Low Risk (Green):** $1 \le \text{RS} \le 7$ (Standard validation).

---

## 2. Comprehensive Risk Register

| Risk ID | Risk Category | Risk Description | L (1-5) | I (1-5) | Score (RS) | Mitigation Strategy | Contingency Plan | Verification Stage |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- | :---: |
| **RSK-01** | Technical (Concurrency) | **Concurrent Double Conversion:** Two sales agents or automated webhook retries trigger conversion of the same lead simultaneously, creating duplicate Deals. | 3 | 5 | **15 (High)** | Implement row-level lock `SELECT ... FOR UPDATE` via `lock_lead()`, and enforce `existing_deal()` check with `if_converted` policy. | Abort secondary conversion; return existing deal ID or raise clean validation error. | Unit, API, Performance Suites |
| **RSK-02** | Data Integrity | **Orphaned / Broken Relationship:** Status update or edit on `CRM Deal` nullifies or breaks the `deal.lead` foreign key link, causing data inconsistency. | 2 | 5 | **10 (Med)** | Write-protection on `lead` link field; cross-workflow regression tests asserting persistence across reloads and status transitions. | Automated data validation script detects and re-links detached deal records. | Unit, API Suites |
| **RSK-03** | Security (RBAC) | **Unauthorized Lead Conversion:** A `Sales User` bypasses UI restrictions to convert or view leads owned by other representatives. | 3 | 4 | **12 (Med)** | Enforce backend permissions in `validate_conversion_access()` and SQL query partitioning in `org_hierarchy.py`. | Immediate HTTP 403 / `frappe.PermissionError` rejection and security audit log generation. | API, Security Suites |
| **RSK-04** | Business Logic | **Invalid State Transition to Lost:** A Deal is moved to `"Lost"` status without providing required business reasons or notes, violating pipeline reporting. | 4 | 3 | **12 (Med)** | Rigorous compound validation in `CRMDeal.validate_lost_reason()` covered by 100% MCC and MC/DC test suites. | UI modal forces input; backend rejection blocks invalid saves. | Unit, API Suites |
| **RSK-05** | Financial Integrity | **Negative Value Ingestion:** Negative numbers entered into deal values or annual revenue, distorting sales forecasting and dashboards. | 3 | 4 | **12 (Med)** | 3-point Boundary Value Analysis tests; data layer validation raising `frappe.NonNegativeError`. | Reject payload before database commit; display user-friendly error. | Unit, Data Gen Suites |
| **RSK-06** | Test Quality | **Weak Test Assertions / Surviving Mutants:** Test suite passes green but asserts only HTTP 200 rather than database state mutations and side-effects. | 4 | 4 | **16 (High)** | Run mutation testing (`mutation_runner.py`); mandate killing all killable mutants and verifying persisted database state. | Enhance test assertions to verify child tables, timestamps, and relational fields. | Mutation, Static Quality Gate |
| **RSK-07** | Non-Functional | **Accessibility Violations:** Critical keyboard navigation and screen reader traps in `ConvertToDealModal.vue` and Deal status dropdowns. | 3 | 3 | **9 (Med)** | Automated `axe-core` and `Lighthouse` scans during Playwright browser automation runs. | Refactor Vue components to include proper ARIA roles, labels, and keyboard listeners. | Accessibility Suite |
| **RSK-08** | Performance | **Pessimistic Lock Degradation:** High volume of concurrent status updates or conversions causes database lock contention and latency spikes. | 3 | 4 | **12 (Med)** | Performance testing with `k6 OSS` at 1 VU and 5 concurrent VUs, measuring p95 response time (tiered targets: $\le 200\text{ ms}$ baseline, $< 300\text{ ms}$ gate, $\le 500\text{ ms}$ peak) and error rate. | Keep lock scope strictly within transaction; optimize database index on `tabCRM Lead.name`. | Performance Suite |
| **PRJ-01** | Project (CI/CD) | **CI Ephemeral Runner Environment Drift:** GitHub Actions clean runner lacks upstream repositories, system dependencies, or browser binaries, causing CI false failures. | 4 | 4 | **16 (High)** | Automated shallow clone in workflow, pinned `requirements.txt`, automated Playwright browser installation step. | Local reproduction scripts in pwsh and dockerized runner fallback. | CI/CD Quality Gate |
| **PRJ-02** | Project (Schema) | **OpenAPI Specification Drift:** Schema constraints in OpenAPI spec drift out of alignment with backend DocType metadata, causing generator invalid payloads. | 2 | 4 | **8 (Med)** | Bidirectional schema validation test suite (`test_generated_data.py`) validating spec against mock fixtures. | Regenerate OpenAPI specification from Frappe DocType schema JSON files. | Data Gen Suite |

---

## 3. Measurable Exit Criteria Tied to Highest Risks

In adherence to project requirements, three measurable, objective exit criteria were established, with two directly tied to the highest-scoring risks:

| Exit Criterion ID | Target Metric | Measurable Threshold | Linked Highest Risk(s) | Verification Evidence |
| :---: | :--- | :--- | :---: | :--- |
| **EC-01 (Functional & Mutation)** | Test Suite Pass Rate & Mutation Kill Rate | **100% Pass (0 failures across all 124 tests)** AND **$\ge 80\%$ Mutation Score (Achieved: 100% of 16 mutants killed)** | **RSK-01** (Score 15)<br>**RSK-06** (Score 16) | 124/124 tests passing; 16/16 AST mutants killed (100.0%) in `tests/team/mutation/mutation_runner.py`. |
| **EC-02 (Security & RBAC)** | Defensive Security & Role Authorization Violations | **0 Critical / High RBAC Bypasses** AND **0 High-Risk Passive Scan Findings** | **RSK-03** (Score 12)<br>**RSK-02** (Score 10) | 6 RBAC access decisions verified (3 allowed, 3 denied); 0 high/critical vulnerabilities in `docs/SECURITY_REPORT.md`. |
| **EC-03 (Performance & Reliability)** | Concurrency Latency & Failure Rate under Load | **$p95 \le 200\text{ ms}$ (1 VU), $p95 < 300\text{ ms}$ (Gate), $p95 \le 500\text{ ms}$ (5 VU Peak)** AND **Unexpected Failure Rate $< 1.0\%$** | **RSK-08** (Score 12)<br>**RSK-01** (Score 15) | k6 OSS benchmarks report $p95 = 1.6\text{--}4.4\text{ ms}$, 0.0% unexpected failures in `docs/PERFORMANCE_REPORT.md`. |

---

## 4. Risk Monitoring & Review Cycle

1. **Milestone Gate Reviews:** At the conclusion of each milestone, the risk register is reviewed to confirm whether test evidence successfully mitigates the targeted risk.
2. **Defect Feedback Loop:** Any discovered defects trigger an immediate re-evaluation of likelihood and impact scores.
