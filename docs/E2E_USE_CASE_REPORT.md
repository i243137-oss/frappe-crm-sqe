# SE3002 SQE Project - Playwright End-to-End Use Case Automation Report

## 1. Overview & Scope
This report documents the design, implementation, and automated browser execution of the **Playwright E2E Use Case Automation Suite** for Frappe CRM.
The suite validates the end-to-end user journeys for the target CRM workflows:
1. **Workflow 1:** Convert Lead to Deal
2. **Workflow 2:** Update Deal Status (Won, Lost, reasons, logs)

All tests execute headlessly on **Chromium** (Playwright 1.65.2) with strict assertion of DOM states, modal dialog interactions, toast notifications, and keyboard navigation.

---

## 2. Test Scenarios & Execution Matrix

| Test ID | Flow Category | Test Name & Target Actions | Expected DOM & System Verification | Outcome |
| :--- | :--- | :--- | :--- | :---: |
| `TC-E2E-01` | **Happy Path** | Lead conversion $\to$ Deal creation $\to$ Transition to Won | - Open Convert modal<br>- Submit valid deal parameters ($85,000.00)<br>- Verify Deal view rendered with linked lead<br>- Click "Mark as Won"<br>- Status updates to `Won`, closed_date populated, probability is 100% | **PASSED** |
| `TC-E2E-02` | **Alternative Flow 1** | Deal Lost with Predefined Standard Reason | - Convert Lead $\to$ Open Lost Modal<br>- Select reason code `Competitor`<br>- Lost notes textarea remains hidden<br>- Status updates to `Lost` | **PASSED** |
| `TC-E2E-03` | **Alternative Flow 2** | Deal Lost with Reason 'Other' & Mandatory Notes | - Convert Lead $\to$ Open Lost Modal<br>- Select reason code `Other`<br>- Form expands with mandatory notes field<br>- Input valid justification notes<br>- Status updates to `Lost` | **PASSED** |
| `TC-E2E-04` | **Exception Flow 1** | Ineligible Lead Conversion Blocked | - Lead marked as `Lost`<br>- Click "Convert to Deal"<br>- Modal blocked from opening<br>- Error toast displayed: *"Cannot convert a Lost lead"* | **PASSED** |
| `TC-E2E-05` | **Exception Flow 2** | Lost Reason & Notes Validation Failure | - Deal Lost submitted with empty reason rejected<br>- Deal Lost submitted with `Other` and blank notes rejected<br>- Error toasts shown; modal remains open | **PASSED** |
| `TC-E2E-06` | **Usability & Accessibility** | Keyboard Navigation & Modal Escape Dismissal | - Open modal via click<br>- Press `Escape` key on keyboard<br>- Active modal cleanly dismissed without submission | **PASSED** |

---

## 3. Playwright Automation Architecture

```
                    +----------------------------------------+
                    | tests/team/e2e/test_crm_use_cases...   |
                    |      (Playwright Test Runner)          |
                    +-------------------+--------------------+
                                        | (sync_playwright)
                                        v
                    +----------------------------------------+
                    |       Headless Chromium Browser        |
                    | (Page interactions, selectors, waits)  |
                    +-------------------+--------------------+
                                        | (HTTP / DOM)
                                        v
                    +----------------------------------------+
                    |    tests/team/e2e/mock_server.py       |
                    |  (SPA Mock Application & API Backend)  |
                    +----------------------------------------+
```

---

## 4. Execution Summary

- **Total Browser Test Cases:** 6
- **Passed:** 6 (100% pass rate)
- **Duration:** 4.42 seconds
- **Platform:** Windows 11 (AMD64), Python 3.12.2, Playwright 1.65.2
- **Command:** `pytest tests/team/e2e/test_crm_use_cases_playwright.py -v`
