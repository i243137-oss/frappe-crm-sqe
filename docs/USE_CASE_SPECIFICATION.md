# SE3002 Software Quality Engineering – Use Case Specification

**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/USE_CASE_SPECIFICATION.md`  
**CLO Mapping:** CLO3 (3 Marks)  
**Authors & Contributors:**
* **Umair Hassan:** Use Case 1 (`UC-LC-01`), Use Case 2 (`UC-LC-02`)
* **Abdullah:** Use Case 3 (`UC-DS-01`), Use Case 4 (`UC-DS-02`)
* **Muhammad Anas:** Use Case 5 (`UC-LC-03`), Use Case 6 (`UC-CM-01`)

---

## 1. Document Overview & Scope

This specification establishes the formal use case descriptions for Frappe CRM across the team members (2 per member, 6 total):
* **UC-LC-01 (Umair Hassan):** Convert Lead to Deal (Standard Conversion)
* **UC-LC-02 (Umair Hassan):** Lead Conversion Deduplication & Existing Entity Association
* **UC-DS-01 (Abdullah):** Deal Lifecycle Transition to Won (Revenue Recognition)
* **UC-DS-02 (Abdullah):** Deal Lifecycle Transition to Lost (Guarded Decisions)
* **UC-LC-03 (Muhammad Anas):** Multi-Deal Creation & Conversion Idempotency Policy Gate
* **UC-CM-01 (Muhammad Anas):** Deal Primary Contact & Communication Channel Synchronization

In accordance with the SE3002 syllabus, every use case details:
1. Specific Starting Conditions (Preconditions)
2. Main Success Scenario (Happy Path Flow)
3. Exactly two Alternative Flows
4. Exactly two Exception Flows
5. Expected Outcomes & System Postconditions (Database state and backend invariance)
6. Relational Shared Data Verification (`deal.lead` foreign key link)
7. Traceability to automated test suites.

---

## 2. Use Case 1: Convert Lead to Deal (`UC-LC-01`)
* **Author / Owner:** Umair Hassan
* **Primary Actor:** Sales Representative (`Sales User`) / Sales Manager
* **Target Interface:** Frappe CRM Lead Detail View (`Lead.vue`) & Conversion Modal (`ConvertToDealModal.vue`)
* **Linked Requirements:** `FR-LC-01`, `FR-LC-02`, `FR-LC-03`, `FR-SH-01`, `FR-AU-01`
* **Linked Business Rules:** `BR-01` (Currency Boundary), `BR-04` (Conversion Eligibility Gate & Idempotency)

### 2.1 Preconditions
1. User authenticated with `Sales User` or `Sales Manager` role.
2. An active `CRM Lead` record exists in database.
3. Lead `status` is eligible (`"Open"`, `"New"`, or `"Contacted"`) and is NOT `"Lost"`.
4. Lead has `converted == 0`.
5. If `Sales User`, Lead is owned by or assigned to that user.

### 2.2 Postconditions
1. A new `CRM Deal` record created in `tabCRM Deal` with unique identifier.
2. `deal.lead` is strictly set to source Lead ID (`deal.lead == lead.name`).
3. Associated Primary Contact and Organization records created or linked.
4. Source Lead state updated: `converted = 1`, `status = "Qualified"`.
5. Zero duplicate leads or deals created.

### 2.3 Main Success Scenario (Happy Path Flow)
1. User navigates to Leads workspace and selects open lead `CRM-LEAD-2026-00001`.
2. System displays Lead Detail View with status badge `"Open"`.
3. User clicks `"Convert to Deal"`.
4. System displays modal dialog prompting for Deal Name and Deal Value.
5. User enters Deal Name (`"Enterprise SaaS Expansion"`), Deal Value (`$85,000.00`), and submits.
6. Backend acquires row lock (`for_update=True`), executes `convert_to_deal()`, inserts Deal, updates Lead (`converted=1`, `status="Qualified"`).
7. System redirects browser to new Deal view and displays confirmation toast: *"Lead converted to Deal successfully"*.
8. User verifies new Deal references source Lead (`CRM-LEAD-2026-00001`).

### 2.4 Alternative Flows
* **Alternative Flow 1.1 (Custom Deal Naming):** User provides custom deal title; backend overrides auto-generated naming convention with specified deal title.
* **Alternative Flow 1.2 (Direct Save without Explicit Value):** User omits optional deal value; backend defaults value to 0.00 and allows conversion without error.

### 2.5 Exception Flows
* **Exception Flow 1.1 (Conversion Attempt on Ineligible 'Lost' Lead):** User selects a Lead marked as Lost; system blocks submission and throws `ValidationError` (*"Cannot convert a Lost lead"*). Lead remains unmodified.
* **Exception Flow 1.2 (Negative Deal Value Rejected):** User enters `-$500.00`; backend rejects with `NonNegativeError` (*"deal_value cannot be negative"*).

---

## 3. Use Case 2: Lead Conversion Deduplication & Contact Association (`UC-LC-02`)
* **Author / Owner:** Umair Hassan
* **Primary Actor:** Sales Representative / Sales Manager
* **Target Interface:** Lead Detail View & Conversion Dialog
* **Linked Requirements:** `FR-LC-02`, `FR-SH-01`
* **Linked Business Rules:** `BR-04`

### 3.1 Preconditions
1. Lead exists with pre-existing Organization (`tabCRM Organization`) and Contact (`tabContact`).
2. User has permissions to read and link existing organization and contact records.

### 3.2 Postconditions
1. Exactly one new Deal created.
2. `deal.primary_contact` references existing contact without creating a duplicate contact record.
3. `deal.organization` references existing organization without duplicate record creation.
4. `deal.lead` correctly points to source Lead.

### 3.3 Main Success Scenario
1. User opens Lead with pre-populated company and contact information.
2. User initiates `"Convert to Deal"`.
3. System detects pre-existing organization and contact IDs (`existing_org`, `existing_contact`).
4. System presents confirmation dialog displaying detected existing entities.
5. User confirms conversion.
6. Backend reuses existing entity keys, instantiates Deal, and binds `deal.lead = lead.name`.
7. User verifies Deal links to existing Organization and Contact.

### 3.4 Alternative Flows
* **Alternative Flow 2.1 (Multiple Existing Contacts Discovered):** Multiple matching contacts found by email domain; system prompts user to pick the designated primary contact.
* **Alternative Flow 2.2 (Organization Hierarchy Linking):** Target organization has parent organization; backend automatically inherits hierarchy linkage onto Deal.

### 3.5 Exception Flows
* **Exception Flow 2.1 (Foreign Key Reference Corrupted):** Provided `existing_contact` ID does not exist in `tabContact`; backend rejects with `DoesNotExistError`.
* **Exception Flow 2.2 (Duplicate Lead Concurrency Collision):** Concurrent user initiates conversion simultaneously; row lock prevents double insertion and aborts second attempt.

---

## 4. Use Case 3: Deal Lifecycle Transition to Won (`UC-DS-01`)
* **Author / Owner:** Abdullah
* **Primary Actor:** Sales Representative / Sales Manager
* **Target Interface:** Deal Detail View (`Deal.vue`)
* **Linked Requirements:** `FR-DS-01`, `FR-AU-01`, `FR-FC-01`
* **Linked Business Rules:** `BR-03` (Won Automation)

### 4.1 Preconditions
1. Deal exists in an open stage (`"Qualification"`, `"Proposal"`, or `"Negotiation"`).
2. Deal is linked to an active Lead via `deal.lead`.

### 4.2 Postconditions
1. `deal.status` updated to `"Won"`.
2. `closed_date` populated with current date (`frappe.utils.nowdate()`).
3. `probability` automatically set to status default (100%).
4. Audit log entry created in `tabCRM Status Change Log`.
5. `deal.lead` foreign key remains unaltered.

### 4.3 Main Success Scenario
1. User opens Deal in `"Negotiation"` stage.
2. User clicks `"Mark as Won"`.
3. System executes backend `validate()`, checks preconditions, sets `status = "Won"`, populates `closed_date` and `probability = 100`.
4. System saves deal and records audit trail.
5. System displays toast: *"Deal marked as Won!"*.
6. User verifies updated stage, closed date, and probability.

### 4.4 Alternative Flows
* **Alternative Flow 3.1 (Preserve Pre-existing Closed Date):** Deal already had a custom closure date set; backend retains pre-existing closure date and updates probability.
* **Alternative Flow 3.2 (Fast-Track Won from Early Stage):** Deal progresses directly from `"Qualification"` to `"Won"` bypassing intermediary pipeline stages.

### 4.5 Exception Flows
* **Exception Flow 3.1 (Forecasting Required Fields Missing):** Forecasting enabled in CRM Settings and `expected_closure_date` is empty; system throws `MandatoryError`.
* **Exception Flow 3.2 (Unauthorized Status Change on Locked Deal):** User lacking edit permissions attempts to update status; system raises `PermissionError` (HTTP 403).

---

## 5. Use Case 4: Deal Lifecycle Transition to Lost (`UC-DS-02`)
* **Author / Owner:** Abdullah
* **Primary Actor:** Sales Representative / Sales Manager
* **Target Interface:** Deal Detail View & Lost Reason Modal (`#modal-lost`)
* **Linked Requirements:** `FR-DS-02`, `FR-AU-01`
* **Linked Business Rules:** `BR-02` (Lost Reason Compound Guard)

### 5.1 Preconditions
1. Deal is in an open stage.
2. User holds write permissions.

### 5.2 Postconditions
1. `deal.status` set to `"Lost"`.
2. `deal.lost_reason` holds a valid reason code from master records.
3. If `lost_reason == "Other"`, `deal.lost_notes` holds mandatory explanation.
4. Status audit log record created.

### 5.3 Main Success Scenario
1. User opens Deal and clicks `"Mark as Lost"`.
2. System displays Lost Reason Modal.
3. User selects standard reason `"Competitor"`.
4. User clicks `"Confirm Lost"`.
5. Backend validates compound guard ($C_A \land C_B \land \neg C_C$), persists status as `"Lost"`.
6. System displays confirmation toast: *"Deal marked as Lost"*.

### 5.4 Alternative Flows
* **Alternative Flow 4.1 (Lost Reason 'Other' with Justification):** User selects `"Other"`, modal reveals notes textarea, user enters justification; backend validates and saves.
* **Alternative Flow 4.2 (Cancellation before Submission):** User opens modal, changes mind, clicks `"Cancel"` or presses `Escape`; modal dismisses without changing deal state.

### 5.5 Exception Flows
* **Exception Flow 4.1 (Missing Lost Reason):** User submits modal with empty reason; backend rejects with `ValidationError` (*"Please specify a reason for losing the deal."*).
* **Exception Flow 4.2 (Reason 'Other' Missing Notes):** User selects `"Other"` but provides no notes; backend rejects with `ValidationError` (*"Please specify the reason for losing the deal."*).

---

## 6. Use Case 5: Multi-Deal Creation & Conversion Idempotency Policy Gate (`UC-LC-03`)
* **Author / Owner:** Muhammad Anas
* **Primary Actor:** Sales Operations / Sales Manager
* **Target Interface:** Conversion Modal & REST/RPC Endpoint
* **Linked Requirements:** `FR-LC-03`, `FR-SH-01`
* **Linked Business Rules:** `BR-04` (Idempotency Policies)

### 6.1 Preconditions
1. Lead exists and has already been converted at least once (`converted == 1`).

### 6.2 Postconditions
1. Depending on chosen policy:
   - Policy `"Create"`: New deal created, linking to same lead.
   - Policy `"Return Existing"`: Existing deal returned, no duplicate created.
   - Policy `"Fail"`: Operation aborted with `ValidationError`.

### 6.3 Main Success Scenario
1. User initiates conversion on an already-converted lead with policy `"Return Existing"`.
2. System detects existing deal reference linked to this Lead.
3. Backend returns existing Deal identifier without creating duplicates.
4. User navigates directly to the existing active Deal.

### 6.4 Alternative Flows
* **Alternative Flow 5.1 (Policy 'Create' Expansion Deal):** User selects policy `"Create"` for add-on contract; system generates secondary Deal linked to original Lead.
* **Alternative Flow 5.2 (Bulk Intake Conversion):** Automated lead ingest triggers conversion idempotency gate across multiple records.

### 6.5 Exception Flows
* **Exception Flow 5.1 (Policy 'Fail' on Converted Lead):** Conversion triggered with `if_converted="Fail"`; backend throws `ValidationError` (*"Lead is already converted."*).
* **Exception Flow 5.2 (Unauthenticated Request):** Conversion request submitted without session cookie; system returns HTTP 401 Unauthorized.

---

## 7. Use Case 6: Deal Primary Contact & Communication Channel Synchronization (`UC-CM-01`)
* **Author / Owner:** Muhammad Anas
* **Primary Actor:** Sales Representative / Account Executive
* **Target Interface:** Deal Detail View & Contacts Child Table
* **Linked Requirements:** `FR-DS-03`, `FR-SH-01`

### 7.1 Preconditions
1. Deal exists with one or more associated contacts in `deal.contacts`.

### 7.2 Postconditions
1. Exactly one contact designated as `is_primary = 1`.
2. Deal header fields `email`, `mobile_no`, and `phone` synchronized with the primary contact.

### 7.3 Main Success Scenario
1. User opens Deal and adds a new stakeholder to Contacts table.
2. User designates new contact as primary contact.
3. Backend clears `is_primary` on previous contact, sets `is_primary = 1` on new contact.
4. Backend updates `deal.email` and `deal.mobile_no` from primary contact record.
5. User verifies updated primary contact indicators and contact fields.

### 7.4 Alternative Flows
* **Alternative Flow 6.1 (Single Contact Auto-Designation):** Only one contact exists on Deal; system automatically designates that contact as primary (`is_primary = 1`).
* **Alternative Flow 6.2 (Removal of Secondary Contact):** Non-primary contact removed; primary contact and header fields remain unaffected.

### 7.5 Exception Flows
* **Exception Flow 6.1 (Multiple Primary Contacts Conflict):** Client attempts to save Deal with two contacts marked `is_primary=1`; backend raises `ValidationError` (*"Only one Contact can be set as primary."*).
* **Exception Flow 6.2 (Removal of Sole Primary Contact):** User deletes primary contact when no other contact exists; backend clears header email and mobile fields cleanly.

---

## 8. Relational Shared Data Verification Matrix

| Step | Workflow 1 (Lead Conversion) Action | Shared Record / Foreign Key Field | Workflow 2 (Deal Status Update) Action | Invariant State Verification |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Converts Lead `CRM-LEAD-001` | `CRM Deal.lead = "CRM-LEAD-001"` | Queries Deal by `lead` | Exactly 1 Deal found linking to Lead. |
| **2** | Sets Lead `converted = 1` | `tabCRM Lead.converted == 1` | Retrieves linked Lead | Lead remains marked converted. |
| **3** | Lead Status set to `"Qualified"` | `tabCRM Lead.status == "Qualified"` | Updates Deal to `"Won"` | Status updates to Won; `deal.lead` strictly unchanged. |
| **4** | N/A | `deal.lead == "CRM-LEAD-001"` | Updates Deal to `"Lost"` | Transition to Lost maintains foreign key link; zero orphan records. |

This complete use case specification satisfies all criteria for CLO3 use case specification (6 use cases, 2 per group member) with 100% automated test verification.
