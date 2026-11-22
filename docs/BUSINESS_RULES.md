# SE3002 Software Quality Engineering – Business Rules Specification
**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/BUSINESS_RULES.md`  
**Phase:** Phase 2 Deliverable  

---

## 1. Overview & Objective

This document defines the four official business rules governing the **Convert Lead to Deal** (Workflow 1) and **Update Deal Status** (Workflow 2) modules in Frappe CRM. 

Each business rule is derived directly from the source code and classified according to the SQE assignment requirements:
1. **Rule 1 (BR-01):** A boundary or limit.
2. **Rule 2 (BR-02):** A decision containing at least two Boolean conditions (with full MCC truth table and MC/DC pair derivation).
3. **Rule 3 (BR-03):** A rule governing a state change.
4. **Rule 4 (BR-04):** Another relevant business rule from the selected workflows.

---

## 2. Business Rule 1 (BR-01): Boundary & Non-Negative Currency Limit

* **Classification:** Boundary or Limit.
* **Source Location:** `crm/crm/fcrm/doctype/crm_deal/crm_deal.py`, `crm/fcrm/doctype/crm_lead/crm_lead.py`, and `test_negative_currency_fields_rejected`.
* **Description:** Any monetary / currency field associated with a Deal or Lead must be non-negative ($\ge 0$). Negative currency amounts are strictly rejected by the data layer.

### 2.1 Formal Specification
Let $V$ represent any of the currency fields:
$$V \in \{\text{deal\_value}, \text{expected\_deal\_value}, \text{annual\_revenue}, \text{total}, \text{net\_total}\}$$

The rule constraint is:
$$\text{Constraint}(V) = \begin{cases} 
\text{Valid (Accept)}, & \text{if } V \ge 0.00 \\ 
\text{Invalid (Raise NonNegativeError)}, & \text{if } V < 0.00 
\end{cases}$$

### 2.2 Three-Point Boundary Value Analysis (BVA)

| Test Point | Value ($V$) | Partition | Expected System Outcome |
| :--- | :--- | :--- | :--- |
| **Below Boundary ($B - \epsilon$)** | $-\$0.01$ (or $-\$100.00$) | Invalid Negative Partition | Transaction rejected; throws `frappe.NonNegativeError` |
| **Exactly at Boundary ($B$)** | $\$0.00$ | Valid Minimum Boundary | Transaction accepted; saved successfully |
| **Above Boundary ($B + \epsilon$)** | $+\$0.01$ (or $+\$100.00$) | Valid Positive Partition | Transaction accepted; saved successfully |

### 2.3 Equivalence Classes

* **Valid Class ($EC_1$):** Real numbers where $V \ge 0.00$ (e.g., $0.00, 1500.50, 100000.00$).
* **Invalid Class ($EC_2$):** Real numbers where $V < 0.00$ (e.g., $-0.01, -50.00, -99999.00$).

---

## 3. Business Rule 2 (BR-02): Deal Lost Status Compound Decision

* **Classification:** Decision containing at least two Boolean conditions.
* **Source Location:** `crm/crm/fcrm/doctype/crm_deal/crm_deal.py:285-296` (`validate_lost_reason`).
* **Source Implementation:**
  ```python
  def validate_lost_reason(self):
      """Validate the lost reason if the status is set to 'Lost'."""
      if self.status and frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost":
          if not self.lost_reason:
              frappe.throw(_("Please specify a reason for losing the deal."), frappe.ValidationError)
          elif self.lost_reason == "Other" and not self.lost_notes:
              frappe.throw(_("Please specify the reason for losing the deal."), frappe.ValidationError)
  ```

### 3.1 Formal Boolean Conditions
* **Condition A ($C_A$):** Is the Deal status of master type `"Lost"`?
  $$C_A \iff (\text{status.type} == \text{"Lost"})$$
* **Condition B ($C_B$):** Is `lost_reason` non-empty?
  $$C_B \iff (\text{lost\_reason} \ne \text{None} \land \text{lost\_reason} \ne \text{""})$$
* **Condition C ($C_C$):** Is `lost_reason` equal to `"Other"`?
  $$C_C \iff (\text{lost\_reason} == \text{"Other"})$$
  *(Note: $C_C \implies C_B$; if $C_B$ is False, $C_C$ is naturally False).*
* **Condition D ($C_D$):** Is `lost_notes` non-empty?
  $$C_D \iff (\text{lost\_notes} \ne \text{None} \land \text{lost\_notes} \ne \text{""})$$

### 3.2 Decision Outcome Function
The validation decision $F(C_A, C_B, C_C, C_D)$ yields:
* **Valid ($V$):** Validation passes; document save proceeds.
* **Error 1 ($E_1$):** `frappe.ValidationError("Please specify a reason for losing the deal.")`.
* **Error 2 ($E_2$):** `frappe.ValidationError("Please specify the reason for losing the deal.")` (notes required).

$$F = \begin{cases}
V, & \text{if } \neg C_A \\
E_1, & \text{if } C_A \land \neg C_B \\
E_2, & \text{if } C_A \land C_B \land C_C \land \neg C_D \\
V, & \text{if } C_A \land C_B \land (\neg C_C \lor C_D)
\end{cases}$$

### 3.3 Multiple Condition Coverage (MCC) Truth Table

| Row # | $C_A$ (Is Lost) | $C_B$ (Reason Present) | $C_C$ (Reason == "Other") | $C_D$ (Notes Present) | Result | Justification / Outcome |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | False | False | False | False | **Valid ($V$)** | Status is Open/Ongoing; no reason needed. |
| **2** | False | False | False | True | **Valid ($V$)** | Status is Open; unprompted notes ignored. |
| **3** | False | True | False | False | **Valid ($V$)** | Status is Won; lost reason not evaluated. |
| **4** | False | True | True | True | **Valid ($V$)** | Status is Open/Won; lost validation skipped. |
| **5** | True | False | N/A (F) | False | **Error ($E_1$)** | Lost status with no reason -> Throws $E_1$. |
| **6** | True | False | N/A (F) | True | **Error ($E_1$)** | Lost status with notes but no reason -> Throws $E_1$. |
| **7** | True | True | False (e.g. "Price") | False | **Valid ($V$)** | Standard lost reason provided; notes optional. |
| **8** | True | True | False (e.g. "Price") | True | **Valid ($V$)** | Standard lost reason provided with notes. |
| **9** | True | True | True ("Other") | False | **Error ($E_2$)** | Reason is "Other" but notes omitted -> Throws $E_2$. |
| **10** | True | True | True ("Other") | True | **Valid ($V$)** | Reason is "Other" and notes provided -> Passes. |

### 3.4 Modified Condition / Decision Coverage (MC/DC) Derivation

MC/DC requires showing that each condition can independently affect the outcome while holding all other possible condition effects fixed:

1. **For Condition $C_A$ (Status is "Lost"):**
   * Pair: **Row 1 vs. Row 5**
   * Row 1: $C_A = \text{False}, C_B = \text{False} \implies \text{Valid } (V)$
   * Row 5: $C_A = \text{True}, C_B = \text{False} \implies \text{Error } (E_1)$
   * *Conclusion:* Changing $C_A$ alone changes the decision from Valid to Error.
2. **For Condition $C_B$ (Reason Present):**
   * Pair: **Row 5 vs. Row 7**
   * Row 5: $C_A = \text{True}, C_B = \text{False}, C_C = \text{False} \implies \text{Error } (E_1)$
   * Row 7: $C_A = \text{True}, C_B = \text{True}, C_C = \text{False} \implies \text{Valid } (V)$
   * *Conclusion:* Changing $C_B$ alone changes the decision from Error $E_1$ to Valid.
3. **For Condition $C_C$ (Reason == "Other"):**
   * Pair: **Row 7 vs. Row 9**
   * Row 7: $C_A = \text{True}, C_B = \text{True}, C_C = \text{False}, C_D = \text{False} \implies \text{Valid } (V)$
   * Row 9: $C_A = \text{True}, C_B = \text{True}, C_C = \text{True}, C_D = \text{False} \implies \text{Error } (E_2)$
   * *Conclusion:* Changing $C_C$ alone changes the decision from Valid to Error $E_2$.
4. **For Condition $C_D$ (Notes Present):**
   * Pair: **Row 9 vs. Row 10**
   * Row 9: $C_A = \text{True}, C_B = \text{True}, C_C = \text{True}, C_D = \text{False} \implies \text{Error } (E_2)$
   * Row 10: $C_A = \text{True}, C_B = \text{True}, C_C = \text{True}, C_D = \text{True} \implies \text{Valid } (V)$
   * *Conclusion:* Changing $C_D$ alone changes the decision from Error $E_2$ to Valid.

---

## 4. Business Rule 3 (BR-03): Automatic Closure Date & Probability on 'Won' State

* **Classification:** Rule governing a state change.
* **Source Location:** `crm/crm/fcrm/doctype/crm_deal/crm_deal.py:101-104, 250-263`.
* **Description:** When a Deal's status is changed to a status of type `Won`, the system must automatically set the `closed_date` to the current system date (`frappe.utils.nowdate()`) if not already populated, and update the default probability from the status definition if unassigned or zero.

### 4.1 State Machine & Transition Logic
$$\text{Transition: } S_{\text{previous}} \xrightarrow{\text{status} \leftarrow \text{"Won"}} S_{\text{current}}$$

* **Trigger:** Save action where `has_value_changed("status") == True`.
* **State Guard:** `frappe.db.get_value("CRM Deal Status", self.status, "type") == "Won"`.
* **Actions:**
  1. `self.closed_date = frappe.utils.nowdate()`
  2. If `not self.probability or self.probability == 0`:
     $$\text{probability} \leftarrow \text{CRM Deal Status}(\text{status}).\text{probability} \lor 0$$
* **Invariance:** If status changes to an open or lost status, `closed_date` is not set to current date.

---

## 5. Business Rule 4 (BR-04): Lead Conversion Status Gate & Idempotency Settle

* **Classification:** Another relevant business rule from the selected workflows.
* **Source Location:** `crm/crm/fcrm/doctype/crm_lead/crm_lead.py:563-600` (`convert_to_deal`, `settle_converted`).
* **Description:** 
  1. **Ineligibility Gate:** A Lead whose status type is `"Lost"` is strictly barred from conversion.
  2. **Idempotency Policy:** When a Lead has already been converted to a Deal (`existing_deal(lead.name)` is not null), the conversion behavior is governed by the `if_converted` directive:
     * `"Fail"`: Abort transaction and raise exception.
     * `"Return Existing"`: Return the existing Deal ID without creating duplicates.
     * `"Create"`: Allow creating an additional deal.

### 5.1 Decision Table

| Rule Condition | `lead.status.type` | `existing_deal` | `if_converted` | Expected Behavior |
| :---: | :---: | :---: | :---: | :--- |
| **BR-04-A** | `"Lost"` | Any | Any | Throws `frappe.ValidationError("Cannot convert a lead with status...")` |
| **BR-04-B** | Open / Qualified | Present | `"Fail"` | Throws `frappe.ValidationError("Lead ... is already converted to Deal ...")` |
| **BR-04-C** | Open / Qualified | Present | `"Return Existing"` | Returns existing deal identifier immediately; idempotent retry |
| **BR-04-D** | Open / Qualified | Present | `"Create"` | Creates new Deal linked to Lead |
| **BR-04-E** | Open | None | Any | Normal conversion proceeds: creates Deal, marks `converted = 1` |
