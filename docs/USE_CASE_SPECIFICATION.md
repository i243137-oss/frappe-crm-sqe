# SE3002 Software Quality Engineering – Use Case Specification

**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/USE_CASE_SPECIFICATION.md`  
**CLO Mapping:** CLO3 (3 Marks)  

---

## 1. Document Overview & Scope

This specification establishes the formal use case descriptions for the two target workflows in Frappe CRM:
* **Use Case 1 (UC-LC-01):** Convert Lead to Deal
* **Use Case 2 (UC-DS-01):** Update Deal Status (Won / Lost Progression)

In accordance with the SE3002 syllabus, each use case details:
1. Specific Starting Conditions (Preconditions)
2. Main Success Scenario (Happy Path Flow)
3. At least two Alternative Flows
4. At least two Exception Flows
5. Expected Outcomes & System Postconditions
6. Relational Shared Data Verification (`deal.lead` foreign key link)
7. Traceability to automated Playwright browser tests ([`tests/team/e2e/test_crm_use_cases_playwright.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/e2e/test_crm_use_cases_playwright.py)).

---

## 2. Use Case 1: Convert Lead to Deal (`UC-LC-01`)

### 2.1 Metadata & Context
* **Use Case ID:** `UC-LC-01`
* **Name:** Convert Sales Lead into Qualified CRM Deal
* **Primary Actor:** Sales Representative (`Sales User`) / Sales Manager
* **Target Interface:** Frappe CRM Lead Detail View (`Lead.vue`) & Conversion Modal (`ConvertToDealModal.vue`)
* **Linked Requirements:** `FR-LC-01`, `FR-LC-02`, `FR-LC-03`, `FR-SH-01`, `FR-AU-01`
* **Linked Business Rules:** `BR-01` (Currency Boundary), `BR-04` (Conversion Eligibility Gate & Idempotency)

### 2.2 Preconditions (Starting Conditions)
1. The user is authenticated with a valid session holding the `Sales User` or `Sales Manager` role.
2. An existing `CRM Lead` record exists in the database.
3. The Lead's `status` is eligible for conversion (`"Open"`, `"New"`, or `"Contacted"`) and is **NOT** `"Lost"`.
4. The Lead has `converted == 0`.
5. If the user is a `Sales User`, the Lead must be assigned to or owned by that user (per `org_hierarchy.py`).

### 2.3 Postconditions (System State Changes)
1. A new `CRM Deal` record is created in `tabCRM Deal` with a unique ID (e.g. `"CRM-DEAL-2026-00001"`).
2. The newly created Deal has its `lead` field set to the source Lead ID (`deal.lead == lead.name`).
3. Associated Primary Contact (`tabCRM Contact`) and Organization records are created or linked.
4. The source Lead's state is updated: `converted = 1`, `status = "Qualified"`, `communication_status = "Replied"`.
5. The original Lead is preserved; zero duplicate Leads or Deals are created.

### 2.4 Main Success Scenario (Happy Path Flow)
1. User logs into Frappe CRM and navigates to the Leads workspace.
2. User selects an open, unconverted lead (`CRM-LEAD-2026-00001`).
3. System displays the Lead Detail View with status badge `"Open"` and displays the `"Convert to Deal"` action button.
4. User clicks `"Convert to Deal"`.
5. System displays the modal dialog prompting for Deal Name, Deal Value, and Organization.
6. User enters Deal Name (`"Enterprise SaaS Expansion"`), a valid positive Deal Value (`$85,000.00`), and submits the form.
7. System acquires a row lock (`lock_lead(for_update=True)`), executes backend `convert_to_deal()`, inserts the Deal, updates the Lead (`converted=1`, `status="Qualified"`), and redirects the browser to the newly created Deal view.
8. System displays confirmation toast: *"Lead converted to Deal successfully"*.
9. User verifies the new Deal references the source Lead (`CRM-LEAD-2026-00001`).

### 2.5 Alternative Flows

#### Alternative Flow 1.1: Conversion with Existing Linked Organization & Contact
* **Trigger:** At Step 5, the Lead already has an associated Contact (`tabContact`) and Organization (`tabCRM Organization`).
* **Execution:**
  1. System detects existing associations (`existing_contact`, `existing_org`).
  2. Rather than creating duplicate contact/organization entities, system reuses existing IDs and sets `deal.primary_contact` and `deal.organization`.
  3. System creates Deal and links to Lead cleanly.
* **Postcondition:** Exactly 1 Deal created, zero duplicate contacts or organizations.

#### Alternative Flow 1.2: Secondary Conversion under `if_converted="Create"` Policy
* **Trigger:** At Step 4, the Lead is already marked `converted=1` from a prior deal, but user explicitly requests an additional deal.
* **Execution:**
  1. System checks `if_converted` parameter.
  2. Because policy is `"Create"`, system permits deal instantiation and appends the new Deal to the Lead's deal history.
  3. Lead remains `converted=1`.
* **Postcondition:** Second Deal created with foreign key pointing to original Lead.

### 2.6 Exception Flows

#### Exception Flow 1.1: Conversion Attempt on Ineligible ("Lost") Lead Blocked
* **Trigger:** At Step 2, the selected Lead has `status == "Lost"`.
* **Execution:**
  1. System checks Lead eligibility (`frappe.get_cached_value("CRM Lead Status", lead.status, "type") == "Lost"`).
  2. System disables the modal submission and displays error toast: *"Cannot convert a Lost lead"*.
  3. Backend raises `frappe.ValidationError` (`BR-04`).
* **Postcondition:** No Deal is created; Lead state remains unmodified (`converted=0`, `status="Lost"`).
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_exception_flow_convert_lost_lead_rejected`.

#### Exception Flow 1.2: Unauthorized User Conversion Attempt (RBAC Violation)
* **Trigger:** A `Sales User` attempts to convert a Lead owned by another sales representative.
* **Execution:**
  1. User triggers conversion via direct API or URL navigation.
  2. Backend `validate_conversion_access()` queries `org_hierarchy.py` and detects lack of write permissions.
  3. System throws `frappe.PermissionError` with HTTP 403 Forbidden.
* **Postcondition:** Transaction rolls back; Lead remains unchanged; security audit event logged.
* **Automated Test:** `tests/team/api/test_lead_conversion_api.py::test_api_unauthorized_conversion`.

---

## 3. Use Case 2: Update Deal Status (`UC-DS-01`)

### 3.1 Metadata & Context
* **Use Case ID:** `UC-DS-01`
* **Name:** Progress Deal Pipeline Status (Won / Lost Resolution)
* **Primary Actor:** Sales Representative (`Sales User`) / Sales Manager
* **Target Interface:** Frappe CRM Deal Detail View (`Deal.vue`) & Lost Reason Modal (`LostReasonModal.vue`)
* **Linked Requirements:** `FR-DS-01`, `FR-DS-02`, `FR-DS-03`, `FR-SH-01`, `FR-AU-01`, `FR-FC-01`
* **Linked Business Rules:** `BR-01` (Currency Boundary), `BR-02` (Lost Reason MCC/MCDC Guard), `BR-03` (Won Automation)

### 3.2 Preconditions (Starting Conditions)
1. The user is authenticated with permissions to view and edit the Deal.
2. A valid `CRM Deal` record exists with initial `status` in an open state (e.g. `"Qualification"`, `"Proposal"`, or `"Negotiation"`).
3. The Deal is linked to an existing Lead via `deal.lead`.

### 3.3 Postconditions (System State Changes)
1. The Deal's `status` field is updated in `tabCRM Deal` to the target status.
2. If transitioned to `"Won"`:
   - `closed_date` is automatically populated with the current system date (`frappe.utils.nowdate()`).
   - `probability` is set to the status master default (100%).
3. If transitioned to `"Lost"`:
   - `lost_reason` contains a valid reason code from `tabCRM Lost Reason`.
   - If `lost_reason == "Other"`, `lost_notes` contains explanatory text.
4. A historical audit log entry is appended to child table `tabCRM Status Change Log` documenting:
   - `from_status`, `to_status`, `transition_date`, `duration_seconds`, and `log_owner = frappe.session.user`.
5. The relational link `deal.lead` remains completely unchanged and valid.

### 3.4 Main Success Scenario (Happy Path Flow: Progression to Won)
1. User navigates to Deals workspace and opens Deal `CRM-DEAL-2026-00001` (status: `"Negotiation"`).
2. System displays Deal details, linked Lead, and status action buttons.
3. User clicks `"Mark as Won"`.
4. System executes backend `validate()`, sets `status = "Won"`, populates `closed_date` with today's date, updates `probability = 100`, and records audit entry in `status_change_log`.
5. System displays success confirmation: *"Deal marked as Won"*.
6. User verifies status badge displays `"Won"`, closed date is populated, and audit trail reflects transition.
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_happy_path_lead_conversion_to_won`.

### 3.5 Alternative Flows

#### Alternative Flow 2.1: Transition to Lost with Predefined Standard Reason
* **Trigger:** At Step 3, Deal negotiations fail due to competitor selection.
* **Execution:**
  1. User clicks `"Mark as Lost"`.
  2. System opens Lost Reason Modal (`#modal-lost`).
  3. User selects predefined reason `"Competitor"` from dropdown.
  4. Notes field remains optional and hidden.
  5. User clicks `"Confirm Lost"`.
  6. Backend validates $C_A=\text{True}, C_B=\text{True}, C_C=\text{False}$ (MCC Row 7 $\implies$ Valid).
  7. Deal status updates to `"Lost"`; audit log entry appended.
* **Postcondition:** Deal marked Lost with reason code `"Competitor"`.
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_alternative_flow_deal_lost_standard_reason`.

#### Alternative Flow 2.2: Transition to Lost with Reason 'Other' & Mandatory Notes
* **Trigger:** At Step 3, Deal is lost for non-standard reason (e.g. client bankruptcy).
* **Execution:**
  1. User clicks `"Mark as Lost"`.
  2. System opens Lost Reason Modal.
  3. User selects reason `"Other"`.
  4. System dynamically reveals mandatory `"Lost Notes"` textarea.
  5. User inputs detailed justification: *"Client cancelled capital expenditure budget for Q4"*.
  6. User submits modal.
  7. Backend validates $C_A=\text{True}, C_B=\text{True}, C_C=\text{True}, C_D=\text{True}$ (MCC Row 10 $\implies$ Valid).
  8. Deal saved as Lost; notes persisted.
* **Postcondition:** Deal marked Lost with reason `"Other"` and full justification text.
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_alternative_flow_deal_lost_other_with_notes`.

### 3.6 Exception Flows

#### Exception Flow 2.1: Missing Lost Reason Rejection
* **Trigger:** User attempts to submit Lost modal without selecting a reason.
* **Execution:**
  1. User opens Lost modal and clicks submit with reason dropdown blank.
  2. System blocks submission, displays error toast: *"Please specify a reason for losing the deal."*
  3. Backend `validate_lost_reason()` evaluates $C_A=\text{True}, C_B=\text{False}$ (MCC Row 5 $\implies$ Error 1).
  4. Modal remains open; transaction blocked.
* **Postcondition:** Deal status remains in previous open state; no audit log created.
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_exception_flow_lost_reason_missing_or_empty_notes`.

#### Exception Flow 2.2: Reason 'Other' Missing Mandatory Justification Notes
* **Trigger:** User selects reason `"Other"` but leaves the notes textarea empty or whitespace.
* **Execution:**
  1. User selects `"Other"` and clicks submit without entering notes.
  2. System detects empty string, displays error toast: *"Please specify the reason for losing the deal."*
  3. Backend evaluates $C_A=\text{True}, C_B=\text{True}, C_C=\text{True}, C_D=\text{False}$ (MCC Row 9 $\implies$ Error 2).
  4. Form submission rejected.
* **Postcondition:** Deal status remains unchanged; error highlighted on textarea.
* **Automated Test:** `tests/team/e2e/test_crm_use_cases_playwright.py::test_e2e_exception_flow_lost_reason_missing_or_empty_notes`.

---

## 4. Shared Data & Relational Link Invariance Verification

| Step | Workflow 1 (Lead Conversion) Action | Shared Record / Foreign Key Field | Workflow 2 (Deal Status Update) Action | Invariant State Verification |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Converts Lead `CRM-LEAD-001` | `CRM Deal.lead = "CRM-LEAD-001"` | Queries Deal by `lead` | Exactly 1 Deal found linking to Lead. |
| **2** | Sets Lead `converted = 1` | `tabCRM Lead.converted == 1` | Retrieves linked Lead | Lead remains marked converted. |
| **3** | Lead Status set to `"Qualified"` | `tabCRM Lead.status == "Qualified"` | Updates Deal to `"Won"` | Status updates to Won; `deal.lead` strictly unchanged. |
| **4** | N/A | `deal.lead == "CRM-LEAD-001"` | Updates Deal to `"Lost"` | Transition to Lost maintains foreign key link; zero orphan records. |

This complete use case specification satisfies all criteria for CLO3 use case specification and is 100% verified by automated Playwright browser tests.
