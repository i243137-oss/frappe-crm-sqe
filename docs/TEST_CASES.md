# SE3002 Software Quality Engineering – Test Cases Specification
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/TEST_CASES.md`  
**Milestone:** Milestone 2 Deliverable  

---

## 1. Test Case Structure & Standards

Every test case follows the IEEE 829 / ISO 29119 specification format:
* **Test Case ID:** Unique hierarchical identifier (`TC-<LEVEL>-<CATEGORY>-<NUM>`).
* **Requirement Reference:** Linked to Functional Requirements (`FR-...`) or Business Rules (`BR-...`).
* **Preconditions:** State of database, active session, and environment prior to test execution.
* **Test Inputs / Parameters:** Concrete test data and payloads.
* **Execution Steps:** Sequential procedural steps.
* **Expected Result & Assertions:** Exact system behavior and persisted database assertions.
* **Postconditions:** Environment cleanup and teardown.

---

## 2. White-Box Unit Test Cases (Milestone 4)

### 2.1 Lead Conversion Unit Tests
* **TC-UNIT-LC-01: Valid Lead Conversion & Field Mapping**
  * **Requirement:** `FR-LC-01`
  * **Preconditions:** Unconverted lead exists with first name, last name, email, organization, annual revenue.
  * **Inputs:** `convert_to_deal(lead=lead.name)`
  * **Assertions:**
    1. Returns valid deal name string (`CRM-DEAL-...`).
    2. Deal document in database has `deal.lead == lead.name`.
    3. Deal document has `deal.organization == lead.organization`.
    4. Lead document has `lead.converted == 1` and `lead.status == "Qualified"`.
* **TC-UNIT-LC-02: Conversion Rejection on Lost Lead (BR-04-A)**
  * **Requirement:** `FR-LC-02`, `BR-04`
  * **Preconditions:** Lead exists with status whose type is `"Lost"`.
  * **Inputs:** `convert_to_deal(lead=lead.name)`
  * **Assertions:** Raises `frappe.ValidationError` matching `"Cannot convert a lead with status"`. No Deal record is inserted.
* **TC-UNIT-LC-03: Repeated Conversion with Fail Policy (BR-04-B)**
  * **Requirement:** `FR-LC-03`, `BR-04`
  * **Preconditions:** Lead was already converted to an existing deal.
  * **Inputs:** `convert_to_deal(lead=lead.name, if_converted="Fail")`
  * **Assertions:** Raises `frappe.ValidationError` matching `"is already converted to Deal"`.
* **TC-UNIT-LC-04: Idempotent Conversion with Return Existing Policy (BR-04-C)**
  * **Requirement:** `FR-LC-03`, `BR-04`
  * **Preconditions:** Lead was already converted to Deal `D1`.
  * **Inputs:** `convert_to_deal(lead=lead.name, if_converted="Return Existing")`
  * **Assertions:** Returns `D1` immediately without inserting a second Deal.
* **TC-UNIT-LC-05: Conversion Write-Permission Enforcement**
  * **Requirement:** `FR-LC-02`, `FR-AU-01`
  * **Preconditions:** User authenticated as `Sales User 2` with no write permission on `Lead 1` (owned by `Sales User 1`).
  * **Inputs:** `convert_to_deal(lead=lead1.name)`
  * **Assertions:** Raises `frappe.PermissionError` matching `"Not allowed to convert Lead to Deal"`.

### 2.2 Deal Status Update & Business Rule Unit Tests
* **TC-UNIT-DS-01: Deal Transition to Won Automated Fields (BR-03)**
  * **Requirement:** `FR-DS-01`, `BR-03`
  * **Preconditions:** Open deal exists with `closed_date = None` and `probability = 0`.
  * **Inputs:** `deal.status = "Won"; deal.save()`
  * **Assertions:** `deal.closed_date == frappe.utils.nowdate()`; `deal.probability == status.probability`.
* **TC-UNIT-DS-02-MCC: Multiple Condition Coverage Suite for BR-02**
  * **Requirement:** `FR-DS-02`, `BR-02`
  * **Inputs & Scenarios:**
    * `TC-UNIT-MCC-01`: Status="Open", Reason=None, Notes=None $\implies$ Valid save.
    * `TC-UNIT-MCC-05`: Status="Lost", Reason=None, Notes=None $\implies$ Raises `ValidationError("Please specify a reason for losing the deal.")`.
    * `TC-UNIT-MCC-07`: Status="Lost", Reason="Price too high", Notes=None $\implies$ Valid save.
    * `TC-UNIT-MCC-09`: Status="Lost", Reason="Other", Notes=None $\implies$ Raises `ValidationError("Please specify the reason for losing the deal.")`.
    * `TC-UNIT-MCC-10`: Status="Lost", Reason="Other", Notes="Client went out of business" $\implies$ Valid save.
* **TC-UNIT-DS-02-MCDC: MC/DC Pair Validations**
  * **Requirement:** `FR-DS-02`, `BR-02`
  * Pair 1 ($C_A$): MCC-01 vs MCC-05 (Status type Lost flips outcome).
  * Pair 2 ($C_B$): MCC-05 vs MCC-07 (Reason presence flips outcome).
  * Pair 3 ($C_C$): MCC-07 vs MCC-09 (Reason "Other" flips outcome to Error).
  * Pair 4 ($C_D$): MCC-09 vs MCC-10 (Notes presence flips outcome to Valid).
* **TC-UNIT-DS-03: Status Change Audit Log & Duration (FR-DS-03)**
  * **Requirement:** `FR-DS-03`
  * **Preconditions:** Deal in "Qualification" status.
  * **Inputs:** Deal status updated to "Negotiation".
  * **Assertions:**
    1. Child table `status_change_log` contains previous status entry with `to == "Negotiation"` and `duration >= 0`.
    2. New active status log created with `from == "Negotiation"` and `log_owner == frappe.session.user`.
* **TC-UNIT-BR1-BVA: 3-Point Boundary Value Analysis on Currency Fields (BR-01)**
  * **Requirement:** `FR-FC-01`, `BR-01`
  * **Inputs:**
    1. Below boundary: `deal_value = -0.01` $\implies$ Raises `frappe.NonNegativeError`.
    2. Exactly at boundary: `deal_value = 0.00` $\implies$ Valid save.
    3. Above boundary: `deal_value = +0.01` $\implies$ Valid save.

---

## 3. API & Integration Test Cases (Milestone 5)

### 3.1 Lead Conversion API Endpoints
* **TC-API-LC-01: Valid Lead Conversion via RPC**
  * **Endpoint:** `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`
  * **Payload:** `{"lead": "LEAD-00001", "deal": {"deal_value": 50000}}`
  * **Assertions:** HTTP 200, `response.json()["message"]` is deal ID, deal exists in database.
* **TC-API-LC-02: Conversion of Ineligible Lost Lead**
  * **Endpoint:** `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`
  * **Payload:** `{"lead": "LEAD-LOST-0001"}`
  * **Assertions:** HTTP 417 / 400, contains message `"Cannot convert a lead with status"`.
* **TC-API-LC-03: Duplicate Deal Prevention on Repeated Call**
  * **Endpoint:** `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`
  * **Payload:** `{"lead": "LEAD-CONV-0001", "if_converted": "Fail"}`
  * **Assertions:** HTTP 417, contains message `"is already converted"`.

### 3.2 Deal Status Update API Endpoints
* **TC-API-DS-01: Valid Status Update to Won via REST**
  * **Endpoint:** `PUT /api/resource/CRM Deal/{name}`
  * **Payload:** `{"status": "Won"}`
  * **Assertions:** HTTP 200, response `data.closed_date == today`.
* **TC-API-DS-02: Invalid Status Update to Lost (Missing Reason) via RPC**
  * **Endpoint:** `POST /api/method/frappe.client.set_value`
  * **Payload:** `{"doctype": "CRM Deal", "name": "DEAL-00001", "fieldname": "status", "value": "Lost"}`
  * **Assertions:** HTTP 417 / 400, `frappe.ValidationError` with `"Please specify a reason"`.

### 3.3 Cross-Workflow Shared Data Integration
* **TC-API-SH-01: End-to-End Pipeline Integration**
  * **Steps:**
    1. `POST /api/resource/CRM Lead` -> create Lead $L_1$.
    2. `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` -> convert $L_1$ to Deal $D_1$.
    3. `GET /api/resource/CRM Deal/D1` -> assert `data.lead == L1`.
    4. `PUT /api/resource/CRM Deal/D1` with `status: "Won"` -> assert update succeeds.
    5. `GET /api/resource/CRM Deal/D1` -> assert `data.lead == L1` remains unbroken.
    6. `GET /api/resource/CRM Lead/L1` -> assert exactly 1 record exists with `converted == 1`.

---

## 4. Playwright End-to-End Test Cases (Milestone 7)

### 4.1 Use Case 1: Convert Lead to Deal
* **TC-E2E-LC-01 (Happy Path):**
  1. Login as Sales User. Navigate to `/crm/leads`.
  2. Open eligible lead from list view.
  3. Click "Convert to Deal" button. Modal dialog appears.
  4. Click "Convert" action button.
  5. Modal closes; page automatically redirects to `/crm/deals/{deal_id}`.
  6. Assert new deal contains lead's contact and organization name.
* **TC-E2E-LC-ALT1 (Alternative Flow 1 - Link Existing Organization):**
  1. Open lead, click "Convert to Deal".
  2. Toggle "Choose Existing Organization" switch on.
  3. Select existing organization from autocomplete link control.
  4. Click "Convert". Assert deal links to existing organization.
* **TC-E2E-LC-ALT2 (Alternative Flow 2 - Link Existing Contact):**
  1. Open lead, click "Convert to Deal".
  2. Toggle "Choose Existing Contact" switch on.
  3. Select existing contact. Click "Convert". Assert deal links to existing contact.
* **TC-E2E-LC-EX1 (Exception Flow 1 - Disabled for Lost Lead):**
  1. Open lead with status "Lost".
  2. Assert "Convert to Deal" button is disabled (`:disabled="isLeadConversionDisabled"`).
  3. Hover on button: tooltip displays `"Cannot convert a lost lead to deal"`.
* **TC-E2E-LC-EX2 (Exception Flow 2 - Mandatory Field Error in Modal):**
  1. Open lead, click "Convert to Deal".
  2. Toggle "Choose Existing Contact" but leave contact empty.
  3. Click "Convert". Assert inline error message displays `"Please select an existing contact"`.
* **TC-E2E-LC-KB (Keyboard Navigation & Focus):**
  1. Open lead using keyboard `Tab` keys.
  2. Focus "Convert to Deal" button, hit `Enter`.
  3. Modal opens; focus trapped in dialog; submit using `Enter`.

### 4.2 Use Case 2: Update Deal Status
* **TC-E2E-DS-01 (Happy Path - Transition to Won):**
  1. Navigate to `/crm/deals`. Open an active deal.
  2. Click status dropdown indicator in header. Select "Won".
  3. Assert status indicator updates to green "Won".
  4. Assert success toast appears: `"Document updated successfully"`.
  5. Inspect Activities tab: status change entry recorded.
* **TC-E2E-DS-ALT1 (Alternative Flow 1 - Kanban Column Drag):**
  1. Switch to Kanban board view on `/crm/deals`.
  2. Drag deal card from "Qualification" column to "Won" column.
  3. Assert card drops in "Won" column and database persists status.
* **TC-E2E-DS-ALT2 (Alternative Flow 2 - Command Palette Status Change):**
  1. Open deal detail view. Press `Cmd+K` / `Ctrl+K`.
  2. Search `"Set status: Won"`, hit `Enter`. Assert status updates immediately.
* **TC-E2E-DS-EX1 (Exception Flow 1 - Lost Reason Modal Required):**
  1. On deal view, change status dropdown to "Lost".
  2. System detects status type Lost and automatically opens `showLostReasonModal`.
  3. Leaving reason empty and clicking save displays validation error.
* **TC-E2E-DS-EX2 (Exception Flow 2 - Lost Notes Required for Other):**
  1. In lost reason modal, select reason `"Other"`.
  2. Leave notes blank and submit.
  3. Assert error: `"Please specify the reason for losing the deal."`.
  4. Enter notes text and submit: save succeeds.

---

## 5. Defensive Security & RBAC Test Cases (Milestone 11)

* **TC-SEC-01 (Sales Manager Global Access):**
  * Authenticate as `Sales Manager`. Access deal owned by another user.
  * Update status to "Won". Assert HTTP 200 / success.
* **TC-SEC-02 (Sales User Scoped Access Denial):**
  * Authenticate as `Sales User A`. Make direct API call `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` for a Lead owned by `Sales User B`.
  * Assert HTTP 403 / `frappe.PermissionError("Not allowed to convert Lead to Deal")`.
* **TC-SEC-03 (Session Cookie Security Attributes):**
  * Send authentication request. Inspect `Set-Cookie` response headers.
  * Assert flags: `HttpOnly=True`, `SameSite=Lax` (or `Strict`), `Path=/`.
* **TC-SEC-04 (SQL Injection & Query Partitioning):**
  * Verify `permission_query_conditions` utilizes Frappe QueryBuilder (`frappe.qb`) parameterized queries, eliminating SQL injection vectors.

---

## 6. Performance & Fault Recovery Test Cases (Milestone 12)

* **TC-PERF-01 (k6 Baseline 1 VU):**
  * Execute `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` for 60 seconds with 1 virtual user.
  * Targets: p95 latency $< 300$ms, failure rate $0\%$.
* **TC-PERF-02 (k6 Concurrency 5 VUs):**
  * Execute concurrent conversion requests with 5 VUs for 60 seconds.
  * Targets: p95 latency $< 600$ms, requests per second (RPS) $\ge 15$, failure rate $< 1\%$.
* **TC-PERF-REC-01 (Controlled Failure & Recovery):**
  * Inject synthetic network timeout / simulated database disconnect during `convert_to_deal` after lock acquisition but before `lead.db_set("converted", 1)`.
  * Assert transaction rollbacks cleanly; no phantom deal created.
  * Retry conversion after recovery: operation succeeds with zero orphaned records.
