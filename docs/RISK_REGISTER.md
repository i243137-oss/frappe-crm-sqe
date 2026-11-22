# SE3002 Software Quality Engineering – Risk Register & Mitigation Strategy
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/RISK_REGISTER.md`  
**Phase:** Phase 2 Deliverable  

---

## 1. Risk Assessment Framework

Risks are evaluated using a standard 5x5 quantitative matrix:
$$\text{Risk Score (RS)} = \text{Likelihood (L: 1–5)} \times \text{Impact (I: 1–5)}$$

* **High Risk (Red):** $15 \le \text{RS} \le 25$ (Immediate mitigation & rigorous testing mandatory).
* **Medium Risk (Yellow):** $8 \le \text{RS} \le 14$ (Monitored with targeted test cases).
* **Low Risk (Green):** $1 \le \text{RS} \le 7$ (Standard validation).

---

## 2. Comprehensive Risk Register

| Risk ID | Risk Category | Risk Description | L (1-5) | I (1-5) | Score (RS) | Mitigation Strategy | Contingency Plan | Verification Phase |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- | :---: |
| **RSK-01** | Technical (Concurrency) | **Concurrent Double Conversion:** Two sales agents or automated webhook retries trigger conversion of the same lead simultaneously, creating duplicate Deals. | 3 | 5 | **15 (High)** | Implement row-level lock `SELECT ... FOR UPDATE` via `lock_lead()`, and enforce `existing_deal()` check with `if_converted` policy. | Abort secondary conversion; return existing deal ID or raise clean validation error. | Phase 4 (Unit), Phase 6 (API), Phase 12 (Perf) |
| **RSK-02** | Data Integrity | **Orphaned / Broken Relationship:** Status update or edit on `CRM Deal` nullifies or breaks the `deal.lead` foreign key link, causing data inconsistency. | 2 | 5 | **10 (Med)** | Write-protection on `lead` link field; cross-workflow regression tests asserting persistence across reloads and status transitions. | Automated data validation script detects and re-links detached deal records. | Phase 4, Phase 5, Phase 7 |
| **RSK-03** | Security (RBAC) | **Unauthorized Lead Conversion:** A `Sales User` bypasses UI restrictions to convert or view leads owned by other representatives. | 3 | 4 | **12 (Med)** | Enforce backend permissions in `validate_conversion_access()` and SQL query partitioning in `org_hierarchy.py`. | Immediate HTTP 403 / `frappe.PermissionError` rejection and security audit log generation. | Phase 5 (API), Phase 11 (Security) |
| **RSK-04** | Business Logic | **Invalid State Transition to Lost:** A Deal is moved to `"Lost"` status without providing required business reasons or notes, violating pipeline reporting. | 4 | 3 | **12 (Med)** | Rigorous compound validation in `CRMDeal.validate_lost_reason()` covered by 100% MCC and MC/DC test suites. | UI modal forces input; backend rejection blocks invalid saves. | Phase 4 (Unit), Phase 5 (API) |
| **RSK-05** | Financial Integrity | **Negative Value Ingestion:** Negative numbers entered into deal values or annual revenue, distorting sales forecasting and dashboards. | 3 | 4 | **12 (Med)** | 3-point Boundary Value Analysis tests; data layer validation raising `frappe.NonNegativeError`. | Reject payload before database commit; display user-friendly error. | Phase 4 (Unit), Phase 6 (Data Gen) |
| **RSK-06** | Test Quality | **Weak Test Assertions / Surviving Mutants:** Test suite passes green but asserts only HTTP 200 rather than database state mutations and side-effects. | 4 | 4 | **16 (High)** | Run mutation testing (`mutmut`); mandate killing all killable mutants and verifying persisted database state. | Enhance test assertions to verify child tables, timestamps, and relational fields. | Phase 8 (Mutation), Phase 9 (Sonar) |
| **RSK-07** | Non-Functional | **Accessibility Violations:** Critical keyboard navigation and screen reader traps in `ConvertToDealModal.vue` and Deal status dropdowns. | 3 | 3 | **9 (Med)** | Automated `axe-core` and `Lighthouse` scans during Playwright browser automation runs. | Refactor Vue components to include proper ARIA roles, labels, and keyboard listeners. | Phase 10 (Accessibility) |
| **RSK-08** | Performance | **Pessimistic Lock Degradation:** High volume of concurrent status updates or conversions causes database lock contention and latency spikes. | 3 | 4 | **12 (Med)** | Performance testing with `k6 OSS` at 1 VU and 5 concurrent VUs, measuring p95 response time and error rate. | Keep lock scope strictly within transaction; optimize database index on `tabCRM Lead.name`. | Phase 12 (Performance) |

---

## 3. Risk Monitoring & Review Cycle

1. **Phase Gate Reviews:** At the conclusion of each phase, the risk register is reviewed to confirm whether test evidence successfully mitigates the targeted risk.
2. **Defect Feedback Loop:** Any discovered defects trigger an immediate re-evaluation of likelihood and impact scores.
