# SE3002 Software Quality Engineering – Software Requirements Specification (SRS)
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/REQUIREMENTS.md`  
**Milestone:** Milestone 2 Deliverable  

---

## 1. Executive Summary & Purpose

This document provides the formal Software Requirements Specification (SRS) for the **Frappe CRM** quality engineering assessment, focusing specifically on two coupled workflows:
1. **Workflow 1: Convert Lead to Deal**
2. **Workflow 2: Update Deal Status**

All functional requirements herein are derived directly from the Frappe CRM upstream codebase (`commit: 678ed0d5c99097674ce45dbbc502d8d2afee927d`, version `2.0.0-dev`). No requirements or validations are speculative or fabricated.

---

## 2. Requirements Summary & Categorization

| Requirement ID | Workflow / Area | Short Description | Source Location |
| :--- | :--- | :--- | :--- |
| **FR-LC-01** | Workflow 1 (Lead Conversion) | Valid Lead to Deal Conversion with Entity Creation & Relational Linking | `crm/fcrm/doctype/crm_lead/crm_lead.py:548-577` |
| **FR-LC-02** | Workflow 1 (Lead Conversion) | Ineligible Status Rejection & Permission Enforcement | `crm/fcrm/doctype/crm_lead/crm_lead.py:568, 579` |
| **FR-LC-03** | Workflow 1 (Lead Conversion) | Concurrency Locking, Idempotency & Duplicate Prevention | `crm/fcrm/doctype/crm_lead/crm_lead.py:564-567, 586-600` |
| **FR-DS-01** | Workflow 2 (Deal Status) | Deal Status Transition to Won with Automated Closure Date & Probability | `crm/fcrm/doctype/crm_deal/crm_deal.py:103-104, 250-263` |
| **FR-DS-02** | Workflow 2 (Deal Status) | Deal Status Transition to Lost with Reason & Notes Validation | `crm/fcrm/doctype/crm_deal/crm_deal.py:285-296` |
| **FR-DS-03** | Workflow 2 (Deal Status) | Status Change Audit Logging & Duration Tracking | `crm/fcrm/doctype/crm_status_change_log/crm_status_change_log.py:45-85` |
| **FR-SH-01** | Shared Data Relationship | Relational Integrity & Non-Duplication Across Workflows | `crm/fcrm/doctype/crm_deal/crm_deal.py:407`, `crm_lead.py:407-439` |
| **FR-AU-01** | Authorization & Scoping | Role-Based Access Control (Sales Manager vs. Sales User Record Scoping) | `crm/permissions/org_hierarchy.py:17-61` |
| **FR-FC-01** | Deal Field Validation | Forecasting Constraints & Non-Negative Currency Boundary Enforcement | `crm/fcrm/doctype/crm_deal/crm_deal.py:275-284, 568-573` |

---

## 3. Detailed Functional Requirements

### 3.1 Workflow 1: Convert Lead to Deal

#### FR-LC-01: Valid Lead to Deal Conversion with Entity Creation & Relational Linking
* **Description:** The system shall convert an open, eligible Lead into a Deal upon user invocation via RPC endpoint `/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`.
* **Preconditions:**
  1. The target `CRM Lead` exists in the database.
  2. The lead status is not of type `Lost`.
  3. The authenticated user has `write` permission on the lead document.
* **Inputs:**
  * `lead` (string, required): Document name / ID of the CRM Lead.
  * `deal` (dict/string, optional): Overrides or additional fields for the new Deal.
  * `existing_contact` (string, optional): ID of an existing Contact to link.
  * `existing_organization` (string, optional): ID of an existing CRM Organization to link.
  * `if_converted` (string, optional, default `"Create"`): Handling policy for already-converted leads (`"Create"`, `"Return Existing"`, `"Fail"`).
* **Processing Logic:**
  1. Acquire pessimistic database lock on `CRM Lead` row (`SELECT ... FOR UPDATE`).
  2. Verify write permission via `frappe.has_permission("CRM Lead", "write", lead)`.
  3. Verify status type is not `Lost`.
  4. Create or reuse linked `Contact` (via email match or provided ID).
  5. Create or reuse linked `CRM Organization` (via name match or provided ID).
  6. Map allowed non-restricted fields from `CRM Lead` to `CRM Deal`.
  7. Set `new_deal.lead = lead.name`.
  8. Set `new_deal.contacts = [{"contact": contact}]`.
  9. Carry over SLA state (`sla_creation`, `response_by`, `sla_status`, `communication_status`, `first_response_time`, `first_responded_on`).
  10. Carry over assignees and restore `deal_owner`.
  11. Insert new Deal into database (`ignore_permissions=True`).
  12. Update Lead: set `converted = 1`, set `status = "Qualified"` (if present), set `communication_status = "Replied"` (if SLA active).
  13. Emit event `emit_lead_converted(...)`.
* **Expected Outputs & Postconditions:**
  * Returns new Deal name/ID (e.g., `CRM-DEAL-2026-00001`).
  * Database state: 1 new `CRM Deal` record created, 1 `CRM Lead` marked `converted = 1`.
  * Deal is linked to original Lead (`deal.lead == lead.name`).
* **Error Handling:**
  * If lead not found: `frappe.DoesNotExistError`.
  * If unauthorized: `frappe.PermissionError("Not allowed to convert Lead to Deal")`.

---

#### FR-LC-02: Ineligible Status Rejection & Permission Enforcement
* **Description:** The system must strictly reject conversion of any Lead whose current status type is `Lost`, or where the user lacks write permission.
* **Preconditions:** A user attempts conversion of a Lead.
* **Processing Logic:**
  1. Inspect user permissions: if user lacks `write` on `CRM Lead`, abort immediately before database lock.
  2. Inspect `frappe.get_cached_value("CRM Lead Status", lead.status, "type")`.
  3. If status type equals `"Lost"`, throw validation exception.
* **Expected Output:**
  * Throws `frappe.ValidationError` with message `_("Cannot convert a lead with status {0}").format(lead.status)`.
  * No `CRM Deal` is inserted; Lead remains untouched in the database.
* **Acceptance Criteria:**
  * Status "Lost" leads cannot be converted under any circumstance.
  * Users without write access receive HTTP 403 / `PermissionError`.

---

#### FR-LC-03: Concurrency Locking, Idempotency & Duplicate Prevention
* **Description:** The system shall serialize concurrent conversion attempts on the same lead and support idempotent execution for automated retries.
* **Preconditions:** Multiple concurrent requests or repeated requests to convert the same Lead.
* **Processing Logic:**
  1. Execute `frappe.qb.from_(table).select(table.name).where(table.name == lead).for_update().run()`.
  2. Check `existing_deal(lead.name)`.
  3. If existing deal exists:
     * If `if_converted == "Fail"`: throw `_("Lead {0} is already converted to Deal {1}")`.
     * If `if_converted == "Return Existing"`: return the name of the existing Deal without creating a duplicate.
     * If `if_converted == "Create"`: proceed with secondary Deal creation.
* **Expected Outputs:**
  * Prevents race conditions and phantom duplicate deals.
  * Deterministic retry support for automation and API integrations.

---

### 3.2 Workflow 2: Update Deal Status

#### FR-DS-01: Deal Status Transition to Won with Automated Closure Date & Probability
* **Description:** When a Deal transitions to a status whose master status type is `Won`, the system shall automatically set the closure date and update default probability.
* **Preconditions:** Deal exists in an open or ongoing status.
* **Inputs:** `status` set to a status where `CRM Deal Status.type == "Won"` (e.g., `"Won"`).
* **Processing Logic:**
  1. Detect change: `self.has_value_changed("status")`.
  2. Query `CRM Deal Status` for `type`.
  3. If `type == "Won"`:
     * Set `self.closed_date = frappe.utils.nowdate()`.
     * If `not self.probability` or `self.probability == 0`: update `self.probability` from `CRM Deal Status.probability`.
* **Expected Outputs & Postconditions:**
  * Deal `status` saved as `"Won"`.
  * Deal `closed_date` populated with today's date (`YYYY-MM-DD`).
  * Updated probability persisted in database.

---

#### FR-DS-02: Deal Status Transition to Lost with Reason & Notes Validation
* **Description:** When a Deal transitions to a status whose type is `Lost`, the system must enforce mandatory provision of a lost reason, and if the reason is `"Other"`, mandatory non-empty lost notes.
* **Preconditions:** Deal exists in any non-lost status.
* **Inputs:**
  * `status`: status name where `type == "Lost"` (e.g., `"Lost"`).
  * `lost_reason` (string, required for Lost).
  * `lost_notes` (text, required if `lost_reason == "Other"`).
* **Processing Logic:**
  1. Check `frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost"`.
  2. If `not self.lost_reason`: throw `_("Please specify a reason for losing the deal.")`.
  3. If `self.lost_reason == "Other"` and `not self.lost_notes`: throw `_("Please specify the reason for losing the deal.")`.
* **Expected Outputs:**
  * If valid: Deal saved with `status = "Lost"`, `lost_reason`, and `lost_notes`.
  * If invalid: Transaction aborted, `frappe.ValidationError` raised with descriptive message.

---

#### FR-DS-03: Status Change Audit Logging & Duration Tracking
* **Description:** On every Deal status change, the system must append an immutable audit log record tracking the transition, duration, and acting user.
* **Preconditions:** Deal document is modified and saved with a new `status`.
* **Processing Logic:**
  1. In `CRMDeal.validate()`, call `add_status_change_log(self)` when `has_value_changed("status")`.
  2. If previous status log exists:
     * Set `last_status_change.to = doc.status`.
     * Set `last_status_change.to_type = to_status_type`.
     * Set `last_status_change.to_date = datetime.now()`.
     * Compute `duration = (to_date - from_date).total_seconds()`.
     * Set `log_owner = frappe.session.user`.
  3. Append new active log entry for the new status:
     * `from = doc.status`, `from_type = to_status_type`, `from_date = datetime.now()`, `log_owner = frappe.session.user`.
* **Expected Outputs & Postconditions:**
  * `CRM Status Change Log` child table in `CRM Deal` updated with completed duration and new active interval.
  * Audit trail viewable in UI Activities tab.

---

### 3.3 Shared Data Consistency & Authorization

#### FR-SH-01: Relational Integrity & Non-Duplication Across Workflows
* **Description:** The system must guarantee that a Lead converted to a Deal maintains unbroken, immutable relational integrity across all subsequent Deal lifecycle operations.
* **Processing Logic:**
  1. In Workflow 1, `CRM Deal.lead` is assigned `lead.name`.
  2. In Workflow 2, status changes, notes updates, and field edits on `CRM Deal` must NEVER alter, overwrite, or nullify `deal.lead`.
  3. The original `CRM Lead` record must not be duplicated or deleted during status changes.
* **Acceptance Criteria:**
  * Querying `CRM Deal` where `name = :deal_id` always yields `lead == :original_lead_id`.
  * Querying `CRM Lead` where `name = :original_lead_id` yields exactly 1 record with `converted == 1`.

---

#### FR-AU-01: Role-Based Access Control & Scoped Record Visibility
* **Description:** The system shall enforce data partitioning between `Sales Manager` and `Sales User` roles via backend permission query conditions.
* **Processing Logic:**
  1. For `Sales Manager`:
     * Permission query condition returns empty string `""` (global access across all records).
  2. For `Sales User`:
     * Permission query condition restricts SQL queries to:
       `(lead_owner == user) OR (name IN (SELECT reference_name FROM tabToDo WHERE allocated_to == user AND status != 'Cancelled'))`.
     * Direct API calls on unassigned/unowned records raise `frappe.PermissionError`.
* **Acceptance Criteria:**
  * A `Sales User` cannot view, convert, or update status of Leads or Deals owned by or assigned to another representative.

---

#### FR-FC-01: Deal Forecasting Constraints & Non-Negative Currency Boundaries
* **Description:** The system shall enforce field-level constraints for forecasting and monetary integrity.
* **Processing Logic:**
  1. If `FCRM Settings.enable_forecasting == 1`:
     * `expected_deal_value` must be provided and $> 0$.
     * `expected_closure_date` must be provided.
  2. Currency validation:
     * `annual_revenue`, `deal_value`, `expected_deal_value`, `total`, and `net_total` must be $\ge 0$.
     * Negative values must raise `frappe.NonNegativeError`.
* **Acceptance Criteria:**
  * Rejects deals with negative monetary values at boundary: $-0.01$ rejected, $0.00$ accepted, $+0.01$ accepted.
