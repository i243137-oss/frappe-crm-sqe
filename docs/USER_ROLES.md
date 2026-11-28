# SE3002 Software Quality Engineering – User Roles & Authorization Specification
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/USER_ROLES.md`  
**Milestone:** Milestone 2 Deliverable  

---

## 1. Overview & Objective

This document specifies the Role-Based Access Control (RBAC) model implemented in Frappe CRM for the **Leads** and **Deals** modules. It identifies two distinct, actual user roles from the codebase:
1. **`Sales Manager`**
2. **`Sales User`**

It details the permission matrices, security enforcement hooks in Python, and authorization boundaries that will be systematically validated in Unit, API, Playwright, and Defensive Security test Milestones.

---

## 2. Identified User Roles

### 2.1 Role 1: Sales Manager
* **Role Identifier:** `"Sales Manager"`
* **Domain Responsibility:** Head of sales, sales executive, or regional sales lead.
* **Access Scope:** Global / Organization-wide visibility (or unrestricted within their hierarchy subtree).
* **Key Capabilities:**
  * View, create, edit, convert, and delete all Leads across the organization.
  * View, create, edit, change status, and delete all Deals across the organization.
  * Configure system layouts, view custom layouts, and edit quick entry field configurations.
  * Reassign leads and deals among sales representatives.
  * Access full status change activity logs across all records.

### 2.2 Role 2: Sales User
* **Role Identifier:** `"Sales User"`
* **Domain Responsibility:** Individual sales development representative (SDR) or account executive (AE).
* **Access Scope:** Strictly scoped to self-owned records and explicitly assigned tasks.
* **Key Capabilities:**
  * Create new Leads and Deals (ownership automatically assigned to themselves).
  * View, edit, and convert Leads where `lead_owner == user` OR where assigned via an active `ToDo`.
  * View, edit, and update status of Deals where `deal_owner == user` OR where assigned via an active `ToDo`.
  * Cannot view, edit, convert, or update records belonging to other representatives.
  * Attempts to access or convert unassigned/unowned records raise `frappe.PermissionError`.

---

## 3. Backend Enforcement Mechanism (`org_hierarchy.py`)

The authorization model is enforced via Frappe hook handlers configured in `crm/crm/hooks.py` and implemented in `crm/crm/permissions/org_hierarchy.py`.

### 3.1 Permission Query Conditions
Whenever a list or document query is executed for `CRM Lead` or `CRM Deal`, Frappe automatically executes:
```python
def permission_query_conditions(user: str | None, doctype: str):
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return ""

    roles = frappe.get_roles(user)
    if "System Manager" in roles:
        return ""

    in_tree = hierarchy_enabled() and _in_hierarchy(user)

    # Sales Manager outside the tree retains the default ie sees everything
    if "Sales Manager" in roles and not in_tree:
        return ""

    owner_field = _OWNER_FIELD[doctype]
    DT = frappe.qb.DocType(doctype)
    Todo = frappe.qb.DocType("ToDo").as_("_todo")

    # Sales User default: own records and records directly assigned to them
    q1 = DT[owner_field] == user
    q2 = DT.name.isin(
        frappe.qb.from_(Todo)
        .select(Todo.reference_name)
        .where((Todo.reference_type == doctype) & (Todo.status != "Cancelled") & (Todo.allocated_to == user))
    )
    return q1 | q2
```

### 3.2 Individual Record Security Checks
For single-record API calls and conversions (`convert_to_deal`, `frappe.client.set_value`):
* `has_lead_permission(doc, ptype, user)`
* `has_deal_permission(doc, ptype, user)`
* `validate_conversion_access(lead, doc)`:
  ```python
  if not frappe.has_permission("CRM Lead", "write", lead):
      frappe.throw(_("Not allowed to convert Lead to Deal"), frappe.PermissionError)
  ```

---

## 4. Role-Permission Matrix

| Operation / Action | Target DocType | `Sales Manager` | `Sales User` (Own / Assigned) | `Sales User` (Other's Record) |
| :--- | :--- | :---: | :---: | :---: |
| **Create Record** | `CRM Lead` | Allowed | Allowed | N/A |
| **View / Read Record** | `CRM Lead` | Allowed | Allowed | **Denied** (HTTP 403 / Omitted from query) |
| **Edit / Save Fields** | `CRM Lead` | Allowed | Allowed | **Denied** (`PermissionError`) |
| **Convert to Deal** | `CRM Lead` | Allowed | Allowed | **Denied** (`PermissionError: Not allowed to convert...`) |
| **Delete Record** | `CRM Lead` | Allowed | Allowed | **Denied** (`PermissionError`) |
| **Create Record** | `CRM Deal` | Allowed | Allowed | N/A |
| **View / Read Record** | `CRM Deal` | Allowed | Allowed | **Denied** (HTTP 403 / Omitted from query) |
| **Update Deal Status** | `CRM Deal` | Allowed | Allowed | **Denied** (`PermissionError`) |
| **Set Primary Contact** | `CRM Deal` | Allowed | Allowed | **Denied** (`PermissionError: Not allowed to set primary...`) |
| **Delete Record** | `CRM Deal` | Allowed | Allowed | **Denied** (`PermissionError`) |
| **View Status Change Log** | `CRM Deal` | Allowed | Allowed | **Denied** (Parent deal unreadable) |
| **Reassign Record Owner** | Both | Allowed | Denied / Ignored | **Denied** |

---

## 5. Security & Test Scenarios

The following specific test scenarios will be implemented in subsequent Milestones:
1. **SC-AU-01:** `Sales Manager` converts any valid Lead to a Deal successfully.
2. **SC-AU-02:** `Sales User` converts a self-owned Lead to a Deal successfully.
3. **SC-AU-03:** `Sales User` attempts to convert another representative's unassigned Lead -> Strictly blocked with `frappe.PermissionError`.
4. **SC-AU-04:** `Sales User` attempts to update status on another representative's Deal -> Strictly blocked with `frappe.PermissionError`.
5. **SC-AU-05:** `Sales User` assigned to a Deal via active `ToDo` can update its status, but once the ToDo is cancelled, write access is revoked.
