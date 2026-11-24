# SE3002 Software Quality Engineering – Comprehensive Viva Voce Defense & Live Task Guide

**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/VIVA_DEFENSE_GUIDE.md`  
**Group Members & Contributors:**  
- **Umair Hassan** (Lead Quality Engineer)
- **Abdullah** (Test Automation Engineer)
- **Muhammad Anas** (Quality & Performance Analyst)

---

## 1. Quick Master Reference for Examiners

| Project Dimension | Verified Fact & Measurement |
| :--- | :--- |
| **Upstream Repository & Commit** | `https://github.com/frappe/crm` at commit `678ed0d5c99097674ce45dbbc502d8d2afee927d` |
| **Target Workflows** | 1. Convert Lead to Deal (`convert_to_deal`)<br>2. Update Deal Status (`validate_lost_reason`, `set_value`) |
| **Total Automated Tests** | **94 / 94 Passing (100% Pass Rate)** |
| **White-Box Coverage** | **100% Statement Coverage, 100% Branch Coverage** on business logic |
| **Formal Logic Verification** | 10-row Multiple Condition Coverage (MCC), 4 MC/DC independent pairs (BR-02), 3-point BVA (BR-01) |
| **Mutation Testing** | **100.0% Kill Score (16 / 16 mutants killed)** |
| **Static Code Complexity** | **Grade A, $V(G) = 7$** on `validate_lost_reason` (derived via 3 independent mathematical formalisms) |
| **Accessibility & Usability** | **0 WCAG 2.1 AA violations**, color contrast remediated from 3.29:1 to 4.97:1, Lighthouse 100/96/100 |
| **Security & RBAC** | 6 evaluated access decisions, session cookie flags (`HttpOnly`, `Secure`, `SameSite=Lax`), OWASP ZAP passive scans |
| **Performance SLA (k6)** | 13,199 requests, $p95 = 1.60\text{--}4.36\text{ ms}$ (SLA $< 300\text{ ms}$), 0.00% errors, atomic rollback recovery |
| **Defects Logged & Resolved**| 4 defects documented with 5 Whys, Ishikawa (Fishbone), and Pareto analysis; all closed |

---

## 2. Architecture & Workflows Defense

### Q1: Why did you test Frappe CRM instead of ERPNext?
**Answer:** The project specification explicitly stated on Page 1: *"The ERPNext example may not be selected"*. Frappe CRM (`frappe/crm`) is Frappe's official standalone, modern CRM MIS built on Frappe Framework v15/v16 with a Vue 3 Tailwind frontend and Python backend, satisfying the requirements without utilizing ERPNext.

### Q2: What is the exact API endpoint and Python function for Lead Conversion?
**Answer:** 
- **RPC Endpoint:** `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`
- **File Location:** `crm/crm/fcrm/doctype/crm_lead/crm_lead.py`
- **Function:** `convert_to_deal(lead, create_deal, deal, ...)`
- **Key Actions:** Verifies permissions via `validate_conversion_access`, locks the lead row with `for_update`, creates linked records (`Organization`, `Contact`), sets `lead.converted = 1`, and creates a `CRM Deal` pointing back to `lead.name`.

### Q3: How is the Shared Data Relationship preserved between Lead and Deal?
**Answer:** In Frappe CRM, `CRM Deal` contains a `Link` field: `lead` (DocType `CRM Lead`). During conversion, `deal.lead = lead.name`. The relationship is bidirectional, referentially invariant, and verified across both workflows:
1. Converting Lead `LEAD-001` creates Deal `DEAL-001` with `deal.lead == "LEAD-001"`.
2. Updating `DEAL-001` status to `Won` or `Lost` in Workflow 2 preserves `deal.lead == "LEAD-001"`.
3. The lead is never duplicated, and subsequent conversion attempts are blocked by idempotency policies (`"Return Existing"`, `"Fail"`).

---

## 3. Business Rules & Formal Verification Defense

### Q4: Explain the 4 Business Rules implemented in your project.
**Answer:**
1. **BR-01 (Non-negative Currency):** Currency fields (`deal_value`, `expected_deal_value`, `annual_revenue`, `total`, `net_total`) must be non-negative ($\ge 0.00$). Negative inputs raise `NonNegativeError`.
2. **BR-02 (Lost Deal Validation):** When a deal's status is changed to `Lost`, `lost_reason` is mandatory. If `lost_reason == "Other"`, explanatory `lost_notes` are strictly mandatory.
3. **BR-03 (Won Automation):** When a deal transitions to `Won`, `closed_date` is automatically set to `nowdate()` and `probability` defaults to the master pipeline stage default.
4. **BR-04 (Lead Conversion Eligibility & Idempotency):** Converted or Lost leads cannot be re-converted unless permitted by an explicit idempotency policy (`"Return Existing"`).

### Q5: How did you prove MC/DC coverage for BR-02?
**Answer:** BR-02 decision condition is:
$$\text{Reject} \iff (A \land \neg B) \lor (A \land B \land C \land \neg D)$$
where:
- Condition $A$: `status == "Lost"`
- Condition $B$: `bool(lost_reason)`
- Condition $C$: `lost_reason == "Other"`
- Condition $D$: `bool(lost_notes)`

We constructed a 10-row Multiple Condition Coverage (MCC) truth table and extracted **4 minimal independent condition pairs** where toggling exactly one condition changes the outcome from Valid to Error while holding other relevant conditions constant:
- **Pair for $A$:** Row 1 (False $\to$ Valid) vs. Row 5 (True $\to$ Error)
- **Pair for $B$:** Row 5 (False $\to$ Error) vs. Row 7 (True $\to$ Valid)
- **Pair for $C$:** Row 7 (False $\to$ Valid) vs. Row 9 (True $\to$ Error)
- **Pair for $D$:** Row 9 (False $\to$ Error) vs. Row 10 (True $\to$ Valid)

### Q6: How was 3-point Boundary Value Analysis applied?
**Answer:** On BR-01 currency boundaries with lower limit $0.00$:
- **Below Boundary:** $-0.01$ (strictly rejected with `NonNegativeError`)
- **Boundary:** $0.00$ (accepted valid lower boundary)
- **Above Boundary:** $+0.01$ (accepted valid partition)

---

## 4. Static Code Complexity & CFG Defense

### Q7: Derive the Cyclomatic Complexity $V(G) = 7$ for `validate_lost_reason`.
**Answer:** The Control Flow Graph (CFG) has:
- Nodes ($N$): **12 nodes**
- Directed Edges ($E$): **17 edges**
- Predicate Nodes ($P$): **6 conditional branch nodes**
- Enclosed Planar Regions ($R$): **6 enclosed regions**

We proved $V(G) = 7$ using **three independent mathematical methods**:
1. **Euler's Formula:** $V(G) = E - N + 2P = 17 - 12 + 2(1) = 7$
2. **Predicate Nodes Formula:** $V(G) = P + 1 = 6 + 1 = 7$
3. **Region Counting Theorem:** $V(G) = R + 1 = 6 + 1 = 7$

All 7 independent basis execution paths are mapped and covered by tests in [`tests/team/unit/test_deal_status_unit.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/unit/test_deal_status_unit.py).

---

## 5. Mutation Testing Defense

### Q8: How did you achieve a 100% Mutation Kill Score?
**Answer:** We built an AST-based mutation test runner ([`tests/team/mutation/mutation_runner.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/mutation/mutation_runner.py)) targeting 16 distinct business rule mutants:
- Relational boundary mutations (`< 0` to `<= 0`)
- Logical operator mutations (`and` to `or`)
- Equality mutations (`== "Other"` to `!= "Other"`)
- Statement deletion mutations (omitting `nowdate()`, audit log suppression, contact linking bypass)

Every one of the 16 synthesized mutants was executed against the unit test suite and **killed (16/16, 100.0%)**. Furthermore, in [`docs/MUTATION_REPORT.md`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/docs/MUTATION_REPORT.md), we categorized surviving mutation patterns into Type A (Unreachable guard), Type B (Equivalent mutant), and Type C (Redundant assignment) with formal mathematical proofs.

---

## 6. Performance, Security & Accessibility Defense

### Q9: What were your k6 performance benchmark results?
**Answer:**
- Executed 4 runs of 60 seconds each using k6 OSS v2.4.0 (1 VU $\times$ 2 runs, 5 VUs $\times$ 2 runs).
- Processed **13,199 total requests** with **0.00% failure rate**.
- **$p95$ Latency:** $1.60\text{ ms} - 4.36\text{ ms}$ (exceeding the $< 300\text{ ms}$ SLA threshold by $> 68\times$).
- **Throughput:** Scaled near-linearly ($4.84\times$) from $18.8\text{ req/s}$ (1 VU) to $91.1\text{ req/s}$ (5 VUs).

### Q10: How does your test suite verify transactional fault recovery?
**Answer:** In [`tests/team/performance/test_failure_and_recovery.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/performance/test_failure_and_recovery.py):
1. **DB Connection Failure:** Injected a database exception during deal insertion mid-conversion. The transaction rolled back atomically: zero Deal records were created in the database, and the Lead remained in convertible `Open` state. Subsequent retry succeeded with zero duplicate records.
2. **Network Timeout Idempotency:** Simulated a client drop and retry. The retry detected that the Lead was already converted and rejected duplicate creation, maintaining referential consistency.

### Q11: What accessibility and security issues did you find and fix?
**Answer:**
- **Accessibility:** axe-core flagged a color contrast violation on `#btn-mark-won` (ratio was 3.29:1, below the 4.5:1 WCAG AA threshold). We remediated it by darkening the background to `#15803d` (4.97:1 ratio) and added a semantic `<main>` tag and polite `aria-live` region, achieving **100/100 Accessibility** in Google Lighthouse.
- **Security:** Evaluated 6 RBAC decisions (Sales Manager, Sales User, Guest). Validated session cookie flags (`HttpOnly`, `Secure`, `SameSite=Lax`), CSRF token protection, and ran OWASP ZAP passive rules (verifying `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`).

---

## 7. Live Task Simulation Scenarios & Walkthrough

During the viva voce, examiners frequently present live coding or debugging challenges. Below are three prepared simulations with exact commands:

### Scenario 1: Examiner asks: "Add a new business rule: Deal Value cannot exceed 10,000,000. Which tests fail and how do you update them?"
1. **Where to Add the Rule:** In `tests/team/fixtures/mock_frappe.py` inside `Document.validate_values()`:
   ```python
   if val is not None and isinstance(val, (int, float)) and val > 10000000:
       throw(f"{f} exceeds maximum allowed value 10,000,000", MaxValueError)
   ```
2. **Predicting Failing Tests:**
   - In `tests/team/api/test_api_bva_and_ep.py`: `test_api_equivalence_partitioning_currency` with value `1000000.0` will still pass (under limit), but any test with $> 10\text{M}$ will be rejected.
   - Run `pytest tests/team/unit/ tests/team/api/ -v` to demonstrate the new assertion.

### Scenario 2: Examiner asks: "Inject a mutant into `crm_deal.py` that bypasses `validate_lost_reason`. Show that mutation testing catches it."
1. **Execution:**
   - Open `tests/team/mutation/mutation_runner.py`.
   - Run: `python tests/team/mutation/mutation_runner.py`
   - Point to `[MUT-03]` or `[MUT-04]`: explain how changing `if self.status == "Lost"` to `!= "Lost"` immediately fails `test_br02_multiple_condition_coverage_mcc`, causing the mutant to be **KILLED**.

### Scenario 3: Examiner asks: "Demonstrate that your CI quality gate blocks a pull request on regression."
1. **Evidence Reference:**
   - Refer to [`docs/CI_CD_REPORT.md`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/docs/CI_CD_REPORT.md) and Pull Request #3 (`feat/blocked-quality-gate-demonstration`, GitHub Actions Run `45003934086`).
   - In PR #3, an intentional boundary inversion mutant was pushed; the quality gate failed at `Run White-Box Unit Tests & Measure Coverage`, successfully preventing merge into `dev`.
