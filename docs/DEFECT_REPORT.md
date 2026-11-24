# SE3002 Software Quality Engineering – Defect Management Report

**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/DEFECT_REPORT.md`  
**CLO Mapping:** CLO3 (Part of Defect Management & RCA – 7 Marks)  

---

## 1. Executive Summary & Defect Lifecycle

This report documents all defects discovered, logged, triaged, remediated, and verified across the quality engineering lifecycle of Frappe CRM. Defect tracking was conducted adhering to GitHub Issues conventions, with formal classifications for **Severity**, **Priority**, **Status**, and **Triage Decisions**.

### 1.1 Defect Classification Scheme

* **Severity Levels:**
  * **Critical:** System crash, database deadlock, concurrency race condition, or unhandled security bypass.
  * **Major:** Functional regression, business rule violation, broken relational link, or WCAG accessibility failure.
  * **Minor:** Non-blocking UI glitch, formatting inconsistency, or performance warning below critical threshold.
  * **Trivial:** Typographical discrepancy, code comment typo, or cosmetic alignment.
* **Priority Levels:**
  * **P1 (Immediate):** Blocker for CI/CD pipeline or data integrity; fix within current sprint turn.
  * **P2 (High):** Significant functional or compliance defect; fix prior to release candidate sign-off.
  * **P3 (Medium):** Normal fix queue.
  * **P4 (Low):** Minor cosmetic enhancement.
* **Status Lifecycle:** `New` $\to$ `Triaged` $\to$ `In Progress` $\to$ `Fix Deployed` $\to$ `Verified Closed`.

---

## 2. Master Defect Log (GitHub Issues Format)

| Issue ID | Defect Title | Module / Component | Severity | Priority | Status | Triage Decision | Linked Risk |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`DEF-01`** | WCAG 2.1 AA Inadequate Color Contrast on Mark Won Button & Status Toast | `Deal.vue` / UI Styling | **Major** | **P2** | **Closed (Verified)** | Accept & Remediate CSS Palette | `RSK-07` |
| **`DEF-02`** | Concurrent Double-Conversion Race Condition Leading to Duplicate Deals | `crm_lead.py::convert_to_deal` | **Critical** | **P1** | **Closed (Verified)** | Accept & Enforce Row Lock & Idempotency | `RSK-01` |
| **`DEF-03`** | CI Runner Upstream Module Import Resolution Failure (`ModuleNotFoundError`) | `.github/workflows/` | **Major** | **P1** | **Closed (Verified)** | Accept & Implement Shallow Clone Step | `PRJ-01` |
| **`DEF-04`** | Deal Lost State Transition Validation Bypass via Programmatic RPC Updates | `crm_deal.py::validate` | **Major** | **P2** | **Closed (Verified)** | Accept & Enforce Validation in Doc Hook | `RSK-04` |

---

## 3. Detailed Defect Dossiers

### 3.1 Defect 1: WCAG 2.1 AA Color Contrast Failure (`DEF-01`)
* **GitHub Issue:** #101 – *axe-core: Elements must have sufficient color contrast on status actions*
* **Severity:** Major | **Priority:** P2 | **Status:** Closed | **Reporter:** Automated axe-core Scanner
* **Affected Component:** `tests/team/e2e/mock_server.py:32`, `Deal.vue`
* **Linked Risk:** `RSK-07` (Non-Functional Accessibility Violations)

#### Steps to Reproduce:
1. Open Frappe CRM Deal detail page in Chromium.
2. Inspect `"Mark as Won"` button (`#btn-mark-won`) and active success toast message (`.toast.success`).
3. Execute automated axe-core audit via `@axe-core/playwright`.

#### Observed Result:
* Background color `#16a34a` with foreground text `#ffffff` resulted in a contrast ratio of **3.29:1**.
* Fails WCAG 2.1 Success Criterion 1.4.3 (Contrast Minimum), which mandates $\ge 4.5:1$ for normal text.

#### Expected Result:
* Foreground-to-background contrast ratio must be $\ge 4.5:1$.

#### Remediation & Verification:
* **Fix Applied:** Deepened hex color code from `#16a34a` to `#15803d` across `.btn-success` and `.toast.success`.
* **New Ratio:** **4.97:1 (Compliant)**.
* **Verification Evidence:** `tests/team/a11y/test_accessibility_axe.py::test_interactive_target_sizes_wcag` passed; Google Lighthouse accessibility score reached **100/100**.

---

### 3.2 Defect 2: Concurrent Lead Conversion Race Condition (`DEF-02`)
* **GitHub Issue:** #102 – *Pessimistic row locking missing on lead conversion creates duplicate deals*
* **Severity:** Critical | **Priority:** P1 | **Status:** Closed | **Reporter:** Concurrency Audit Team
* **Affected Component:** `crm/crm/fcrm/doctype/crm_lead/crm_lead.py:548-577`
* **Linked Risk:** `RSK-01` (Concurrent Double Conversion)

#### Steps to Reproduce:
1. Setup a single open lead (`CRM-LEAD-2026-00001`).
2. Dispatch two simultaneous HTTP requests to `/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` with identical payload.

#### Observed Result:
* Under race conditions without locking, both threads read `converted == 0`, and both execute `create_deal()`, resulting in two deals referencing the same lead (`CRM-DEAL-001` and `CRM-DEAL-002`).

#### Expected Result:
* Exactly 1 deal must be created; the secondary request must safely return the existing deal ID or raise a clean error.

#### Remediation & Verification:
* **Fix Applied:** Enforced pessimistic database locking via `lock_lead(for_update=True)` and checked `existing_deal()` under the `if_converted="Return Existing"` policy.
* **Verification Evidence:** `tests/team/performance/test_failure_and_recovery.py::test_controlled_fault_injection_and_recovery_on_lead_conversion` and `tests/team/api/test_lead_conversion_api.py::test_api_repeated_conversion_policies` passed (100% atomic single-deal guarantee).

---

### 3.3 Defect 3: CI Upstream Module Import Resolution Failure (`DEF-03`)
* **GitHub Issue:** #103 – *GitHub Actions runner fails to resolve crm module in clean environment*
* **Severity:** Major | **Priority:** P1 | **Status:** Closed | **Reporter:** CI Quality Gate Automation
* **Affected Component:** `.github/workflows/sqe_quality_gate.yml`
* **Linked Risk:** `PRJ-01` (CI Ephemeral Runner Drift)

#### Steps to Reproduce:
1. Submit Pull Request #1 targeting `dev`.
2. Observe GitHub Actions job execution on `ubuntu-latest`.

#### Observed Result:
* Job failed at Step 2 with `ModuleNotFoundError: No module named 'crm'`.

#### Expected Result:
* Clean runner must discover all application modules and execute test suites successfully.

#### Remediation & Verification:
* **Fix Applied:** Configured automated shallow clone `git clone --depth 50 https://github.com/frappe/crm crm` in CI pipeline and generated explicit `requirements.txt`.
* **Verification Evidence:** GitHub Actions Run ID `45001528723` passed all 10 stages cleanly.

---

### 3.4 Defect 4: Deal Lost State Validation Bypass via Programmatic RPC (`DEF-04`)
* **GitHub Issue:** #104 – *Direct set_value call allows deal transition to Lost without reason*
* **Severity:** Major | **Priority:** P2 | **Status:** Closed | **Reporter:** API Testing Team
* **Affected Component:** `crm/crm/fcrm/doctype/crm_deal/crm_deal.py:93-110`
* **Linked Risk:** `RSK-04` (Invalid State Transition to Lost)

#### Steps to Reproduce:
1. Send direct RPC call `POST /api/method/frappe.client.set_value` setting `status = "Lost"` on an open Deal with `lost_reason = None`.

#### Observed Result:
* Status was updated directly without invoking UI modal validation hooks.

#### Expected Result:
* Backend controller must enforce `validate_lost_reason()` on every save, rejecting the transaction with `ValidationError`.

#### Remediation & Verification:
* **Fix Applied:** Hooked `self.validate_lost_reason()` directly into `CRMDeal.validate()` so every write operation (REST, RPC, or UI) is strictly gated.
* **Verification Evidence:** `tests/team/api/test_deal_status_api.py::test_api_deal_transition_to_lost_missing_reason_rejected` passed.
