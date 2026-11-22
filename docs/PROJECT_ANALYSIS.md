# SE3002 Software Quality Engineering – Project Analysis & Workflow Discovery
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/PROJECT_ANALYSIS.md`  
**Phase:** Phase 1 Deliverable  

---

## 1. Repository Information & Environment

| Property | Value |
| :--- | :--- |
| **Repository URL** | [https://github.com/frappe/crm](https://github.com/frappe/crm) |
| **Cloned Commit Hash** | `678ed0d5c99097674ce45dbbc502d8d2afee927d` |
| **Git Reference / Tag** | `assets-develop-151-g678ed0d` |
| **Application Version** | `2.0.0-dev` (`crm/crm/__init__.py`) |
| **Framework Compatibility** | Frappe Framework (`>=16.0.0-dev, <=17.0.0-dev`) |
| **Runtime Language** | Python `>=3.10`, Node.js `>=20` |
| **Backend Framework** | Frappe Framework (Metadata-driven MVC, Werkzeug WSGI, MariaDB / PostgreSQL / SQLite ORM) |
| **Frontend Framework** | Vue 3 (Composition API / `<script setup>`), Tailwind CSS, Frappe UI (`@frappe/frappe-ui`), Vite |
| **Testing Infrastructure** | pytest, coverage.py, Playwright (`@playwright/test` v1.49.0), Requests, OpenAPI spec |

---

## 2. Repository Architecture

```text
frappe-crm-sqe/
├── crm/                             # Cloned upstream Frappe CRM repository
│   ├── crm/                         # Python application package
│   │   ├── api/                     # Whitelisted RPC/REST API modules (auth, doc, session, form, etc.)
│   │   ├── fcrm/                    # Core CRM domain DocTypes
│   │   │   └── doctype/
│   │   │       ├── crm_lead/        # CRM Lead DocType (model, validations, convert_to_deal)
│   │   │       ├── crm_deal/        # CRM Deal DocType (model, validations, status transitions)
│   │   │       ├── crm_deal_status/ # Deal Status master configuration
│   │   │       ├── crm_lead_status/ # Lead Status master configuration
│   │   │       ├── crm_status_change_log/ # Audit trail for status transitions
│   │   │       ├── crm_lost_reason/ # Lost reason master definitions
│   │   │       └── ...
│   │   ├── permissions/             # Permission hooks & sales hierarchy query conditions
│   │   └── tests/                   # Upstream integration test suite
│   ├── frontend/                    # Vue 3 SPA frontend
│   │   └── src/
│   │       ├── pages/               # Lead.vue, Deal.vue, etc.
│   │       ├── components/          # ConvertToDealModal.vue, FieldLayout, Activities
│   │       └── data/                # document.js (reactive doc resource, save handlers)
│   ├── e2e/                         # Upstream Playwright test setup
│   └── pyproject.toml               # Python project configuration
├── docs/                            # SQE project documentation suite
└── tests/team/                      # Team-written test suite (strictly separate from upstream)
```

---

## 3. Workflow 1 Deep Dive: Convert Lead to Deal

### 3.1 Trace: Frontend to Database
1. **User Action:** In `crm/frontend/src/pages/Lead.vue` (lines 40–51), the user opens a lead. If the lead is not in a "Lost" status, the `Convert to Deal` button is enabled (`variant="solid"`). Clicking it sets `showConvertToDealModal = true`.
2. **Modal Configuration:** In `crm/frontend/src/components/Modals/ConvertToDealModal.vue` (lines 127–186), the user can configure an existing or new organization and contact, optional deal details, and click "Convert".
3. **Frontend API Call:** The modal triggers:
   ```javascript
   await call('crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal', {
     lead: props.lead.name,
     deal: deal.doc,
     existing_contact: existingContact.value,
     existing_organization: existingOrganization.value,
   })
   ```
4. **Backend Endpoint:** `@frappe.whitelist() def convert_to_deal(...)` located in `crm/crm/fcrm/doctype/crm_lead/crm_lead.py` (lines 548–577).
5. **Security & Permission Check:**
   - Calls `validate_conversion_access(lead, doc)` (lines 579–584):
     `frappe.has_permission("CRM Lead", "write", lead)` is asserted.
     If the user lacks permission, it throws `frappe.PermissionError(_("Not allowed to convert Lead to Deal"))`.
6. **Concurrency & Locking:**
   - Calls `lock_lead(lead)` (lines 586–590):
     `frappe.qb.from_(table).select(table.name).where(table.name == lead).for_update().run()` applies a pessimistic database row lock.
7. **Business Rule Validations:**
   - **Ineligible Status Check:**
     `if frappe.get_cached_value("CRM Lead Status", lead.status, "type") == "Lost":`
     `frappe.throw(_("Cannot convert a lead with status {0}").format(lead.status))`
   - **Duplicate / Idempotency Check:**
     Checks `existing_deal(lead.name)`.
     If already converted and `if_converted == "Fail"`, it throws `_("Lead {0} is already converted to Deal {1}")`.
8. **Entity Creation & Linking:**
   - Calls `lead.create_contact(existing_contact, False)` -> creates or links a Frappe `Contact`.
   - Calls `lead.create_organization(existing_organization)` -> creates or links a `CRM Organization`.
   - Calls `lead.create_deal(contact, organization, deal)`:
     - Copies fields from `CRM Lead` to `CRM Deal` (skipping non-transferable layout/system fields).
     - Sets `new_deal.lead = self.name` (establishing the relational link).
     - Sets `new_deal.contacts = [{"contact": contact}]`.
     - Re-links SLA data (`sla_creation`, `response_by`, `sla_status`, `communication_status`).
     - Transfers assignees and preserves `deal_owner`.
     - Inserts the new deal document into the database.
9. **Post-Conversion State Update:**
   - Calls `mark_converted(lead)`:
     - `lead.db_set("status", "Qualified")` (if the Qualified status exists).
     - `lead.db_set("converted", 1)`.
     - Sets `communication_status = "Replied"` if SLA is active.
   - Calls `emit_lead_converted(lead, new_deal, contact, organization)`.
10. **Frontend Navigation:** On receiving the new deal identifier, the modal closes and the router navigates to `/crm/deals/{new_deal_id}`.

---

## 4. Workflow 2 Deep Dive: Update Deal Status

### 4.1 Trace: Frontend to Database
1. **User Action:** In `crm/frontend/src/pages/Deal.vue` (lines 26–38 and 595–600), the user selects a status from the status dropdown, changes column in Kanban, or uses the command palette.
2. **Frontend Handler:** `triggerStatusChange(value)` calls `triggerOnChange('status', value)` and then `setLostReason()`.
3. **Frontend API Call:**
   - If changing to "Lost", opens `showLostReasonModal`.
   - Otherwise, triggers `document.save.submit()` which invokes `frappe.client.set_value` or REST `PUT /api/resource/CRM Deal/{dealId}` with payload `{"status": new_status}`.
4. **Backend Execution:** Handled by `CRMDeal.validate()` in `crm/crm/fcrm/doctype/crm_deal/crm_deal.py` (lines 93–110).
5. **Business Rule Validations:**
   - **Status Change Audit:**
     `if self.has_value_changed("status"): add_status_change_log(self)`
     Appends a row to child table `status_change_log` (`CRM Status Change Log`), records previous status, new status, timestamp, calculated duration in seconds, and `log_owner = frappe.session.user`.
   - **Won State Rule:**
     `if frappe.db.get_value("CRM Deal Status", self.status, "type") == "Won": self.closed_date = frappe.utils.nowdate()`
   - **Lost State Rule (`validate_lost_reason`):**
     If status type is "Lost":
     - `if not self.lost_reason: frappe.throw(_("Please specify a reason for losing the deal."), frappe.ValidationError)`
     - `elif self.lost_reason == "Other" and not self.lost_notes: frappe.throw(_("Please specify the reason for losing the deal."), frappe.ValidationError)`
   - **Forecasting Rule (`validate_forecasting_fields`):**
     If `FCRM Settings.enable_forecasting` is enabled:
     - `expected_deal_value` cannot be empty or 0.
     - `expected_closure_date` is mandatory.
   - **Currency Constraints:**
     All monetary amounts (`annual_revenue`, `deal_value`, `expected_deal_value`, `total`, `net_total`) must be non-negative (`frappe.NonNegativeError`).
   - **Primary Contact Constraint:**
     Only one contact in `contacts` table can have `is_primary = 1`.
6. **Persisted Record:** Document is saved to `tabCRM Deal` in the database, with child rows in `tabCRM Status Change Log`.

---

## 5. Shared Data Relationship Between Workflows

1. **Foreign Key Integrity:**
   - `CRM Deal` contains the field `lead` (DF.Link to `CRM Lead`).
   - When Workflow 1 executes, `lead.create_deal()` explicitly assigns `new_deal.lead = self.name`.
2. **Non-Duplication:**
   - `existing_deal(lead.name)` searches `tabCRM Deal` where `lead = %s`.
   - The lead's `converted` flag is set to `1`.
3. **Relationship Invariance Under Status Updates:**
   - In Workflow 2, updating `status` on `CRM Deal` executes `CRMDeal.validate()`.
   - The `lead` link field is untouched and immutable during status transitions.
   - The relationship persists through reloads, updates, and won/lost closures.

---

## 6. Actual API Endpoints Discovered

| Workflow | HTTP Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Workflow 1** | `POST` | `/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` | Core conversion RPC: validates access, locks lead, creates Deal/Contact/Org, marks lead converted. |
| **Workflow 1 & 2** | `GET` | `/api/resource/CRM Lead/{id}` | Fetches Lead document state. |
| **Workflow 1 & 2** | `POST` | `/api/resource/CRM Lead` | Creates synthetic test Lead. |
| **Workflow 1 & 2** | `GET` | `/api/resource/CRM Deal/{id}` | Fetches Deal document state. |
| **Workflow 1 & 2** | `POST` | `/api/resource/CRM Deal` | Creates Deal directly via REST API. |
| **Workflow 2** | `PUT` | `/api/resource/CRM Deal/{id}` | REST update of Deal fields including `status`, `lost_reason`, `lost_notes`. |
| **Workflow 2** | `POST` | `/api/method/frappe.client.set_value` | Desk/RPC update of single or multiple document fields. |
| **Workflow 2** | `POST` | `/api/method/frappe.desk.form.save.savedocs` | Full form submit endpoint used by Frappe UI. |
| **Workflow 1 & 2** | `GET` | `/api/method/crm.fcrm.doctype.crm_deal.api.get_deal_contacts` | Retrieves linked contacts with primary status. |
| **Workflow 2** | `POST` | `/api/method/crm.fcrm.doctype.crm_deal.crm_deal.set_primary_contact` | Enforces primary contact selection. |

---

## 7. Identified Business Rules for Rigorous Testing

1. **BR-1 (State Transition Gate):**
   A Lead with a status type of `Lost` cannot be converted to a Deal.
   - Implementation: `crm/fcrm/doctype/crm_lead/crm_lead.py` lines 568–569:
     ```python
     if frappe.get_cached_value("CRM Lead Status", lead.status, "type") == "Lost":
         frappe.throw(_("Cannot convert a lead with status {0}").format(lead.status))
     ```
2. **BR-2 (Compound Boolean Decision with Limit/Boundary):**
   When Deal status is changed to a status of type `Lost`, a lost reason is required. If and only if `lost_reason == "Other"`, `lost_notes` must also be non-empty.
   - Implementation: `crm/fcrm/doctype/crm_deal/crm_deal.py` lines 285–293:
     ```python
     if self.status and frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost":
         if not self.lost_reason:
             frappe.throw(_("Please specify a reason for losing the deal."), frappe.ValidationError)
         elif self.lost_reason == "Other" and not self.lost_notes:
             frappe.throw(_("Please specify the reason for losing the deal."), frappe.ValidationError)
     ```
   - *Ideal candidate for Multiple Condition Coverage (MCC) and MC/DC pair derivation in Phase 4.*
3. **BR-3 (Automatic State & Date Calculation on Transition):**
   When Deal status transitions to a status of type `Won`, `closed_date` is automatically populated with the current date (`frappe.utils.nowdate()`), and default probability is updated from the status master if not previously set.
   - Implementation: `crm/fcrm/doctype/crm_deal/crm_deal.py` lines 103–104, 250–263.
4. **BR-4 (Boundary & Non-Negative Limit on Currency Fields):**
   Monetary values (`deal_value`, `expected_deal_value`, `annual_revenue`, `total`, `net_total`) must be non-negative ($\ge 0$). Any negative input is strictly rejected with `frappe.NonNegativeError`.
   - Implementation: Frappe DocField Currency validation and `test_negative_currency_fields_rejected`.

---

## 8. User Roles & Permissions Discovery

| Role | Permissions & Access Control | Actual Code Implementation |
| :--- | :--- | :--- |
| **Sales Manager** | Full access to read, write, create, and delete Leads and Deals across the entire system (or full subtree if hierarchy enabled). Can manage settings and layouts. | `crm/permissions/org_hierarchy.py` lines 31–32 (`roles = frappe.get_roles(user); if "Sales Manager" in roles and not in_tree: return ""`). |
| **Sales User** | Restricted access. Can only read and write Leads and Deals that they own (`lead_owner` / `deal_owner == user`) or that are assigned to them via an active `ToDo`. Access to unassigned records is strictly blocked. | `crm/permissions/org_hierarchy.py` lines 53–60 (`q1 = DT[owner_field] == user; q2 = DT.name.isin(frappe.qb.from_(Todo)...allocated_to == user)`). |

---

## 9. Comprehensive Implementation Plan (Phases 2 to 13)

| Phase | Title | Planned Implementation & Deliverables | Mapping to 120-Mark Requirements |
| :--- | :--- | :--- | :--- |
| **Phase 2** | Requirements, Business Rules, Roles & Test Planning | Author `docs/REQUIREMENTS.md` (8+ functional requirements), `docs/BUSINESS_RULES.md` (formal specifications, truth tables), `docs/USER_ROLES.md`, `docs/TEST_PLAN.md`, `docs/RISK_REGISTER.md`, `docs/TRACEABILITY_MATRIX.md`, `docs/TEST_CASES.md`. | Section 3, Section 16 requirements. |
| **Phase 3** | Test Infrastructure & Synthetic Data | Set up standalone team test framework in `tests/team/`, isolate from upstream tests. Configure pytest fixtures, mock database/API adapters, synthetic seed generator. | Section 4, Section 18 restrictions. |
| **Phase 4** | White-Box Unit Testing & Coverage | Implement exhaustive unit tests in `tests/team/unit/`: 100% statement and branch coverage of business logic, MCC truth tables, MC/DC pairs for BR-2, boundary tests for BR-4. Run coverage.py and generate `docs/UNIT_TEST_REPORT.md`. | Section 5 (Unit Testing, MCC, MC/DC). |
| **Phase 5** | API & Integration Testing | Implement pytest + Requests suite in `tests/team/api/`: Lead conversion, Deal status updates, cross-workflow integration, 3-point BVA, equivalence partitions. Generate `docs/API_TEST_REPORT.md`. | Section 6 (API & Integration). |
| **Phase 6** | OpenAPI Data Generator | Author `crm_spec.json` OpenAPI definition, implement Python generator `tests/team/generator/data_generator.py` producing BVA and EP datasets. Verify dynamic constraint changes. | Section 7 (Test Data Generator). |
| **Phase 7** | Playwright Use Case Automation | Implement end-to-end tests in `tests/team/e2e/`: Lead conversion and Deal status update happy path, 2 alternative flows each, 2 exception flows each, keyboard navigation, a11y focus tests. | Section 8 (Playwright Automation). |
| **Phase 8** | Mutation Testing & CI Quality Gates | Implement mutation testing (mutmut / custom AST mutation operator), analyze 15+ mutants, kill killable mutants. Create GitHub Actions workflow (`.github/workflows/sqe_quality_gate.yml`). Generate `docs/MUTATION_REPORT.md`. | Section 9, Section 11 (Mutation & CI). |
| **Phase 9** | SonarQube & Static Analysis | Configure SonarQube / SonarCloud scanner, extract metrics (cyclomatic complexity, duplications, code smells). Draw CFG for BR-2 and calculate $M = E - N + 2P$. Document in `docs/SONARQUBE_REPORT.md`. | Section 10 (Static Analysis & CFG). |
| **Phase 10** | Accessibility & Usability | Run axe-core and Lighthouse accessibility, SEO, best practices audits on Leads and Deals screens. Fix identified accessibility defects, produce before-and-after audit reports in `docs/ACCESSIBILITY_REPORT.md`. | Section 12 (Accessibility & axe-core). |
| **Phase 11** | Defensive Security Assessment | Construct role-permission matrix (Sales User vs. Sales Manager), execute 4+ access tests, inspect cookie flags (HttpOnly, SameSite, Secure), passive scanner checks, audit dependencies. Generate `docs/SECURITY_REPORT.md`. | Section 13 (Security & RBAC). |
| **Phase 12** | Performance & Recovery | Implement k6 performance test scripts for API operations (1 VU and 5 concurrent VUs, 60s sustained), report p95 latency and RPS. Implement controlled failure & recovery test. Generate `docs/PERFORMANCE_REPORT.md`. | Section 14 (k6 & Fault Recovery). |
| **Phase 13** | Final Documentation & Completion Report | Complete remaining documentation: `DEFECT_REPORT.md`, `ROOT_CAUSE_ANALYSIS.md` (5 Whys & Fishbone), `WEEKLY_PROGRESS.md`, `TEST_COMPLETION_REPORT.md`, and `AI_USE_RECORD.md`. Conduct final verification. | Section 15, 16, 17 completion. |

---

## 10. Phase 1 Verification & Quality Review

- [x] Inspected the official Frappe CRM repository (`https://github.com/frappe/crm`).
- [x] Identified exact commit hash (`678ed0d5c99097674ce45dbbc502d8d2afee927d`) and version (`2.0.0-dev`).
- [x] Traced Workflow 1 ("Convert Lead to Deal") across Vue UI components, whitelisted RPC API, DocType model, validations, and database mutations.
- [x] Traced Workflow 2 ("Update Deal Status") across UI status selectors, REST/RPC endpoints, DocType lifecycle hooks, and audit log tables.
- [x] Verified shared data relationships (`CRM Deal.lead` link, non-duplication, state persistence).
- [x] Identified 4 verified business rules from Frappe CRM code (BR-1 status gate, BR-2 lost reason compound rule, BR-3 won date automation, BR-4 non-negative currency boundary).
- [x] Identified Sales User and Sales Manager roles and permission query hooks in `org_hierarchy.py`.
- [x] Formulated detailed roadmap for Phases 2–13 adhering to all assignment guidelines.
