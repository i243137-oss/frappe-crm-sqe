# Accessibility (a11y) & Usability WCAG 2.1 AA Audit Report

## 1. Executive Summary
As part of the SE3002 Software Quality Engineering (SQE) project for **Frappe CRM**, an automated accessibility and usability audit was conducted on the core Lead Conversion and Deal Lifecycle user interfaces. The evaluation verifies compliance against **Web Content Accessibility Guidelines (WCAG) 2.1 Level A and Level AA standards**, Section 508, and EN 301 549 accessibility requirements.

Testing was executed using industry-standard **axe-core (v4.12)** via `axe-playwright-python` integrated into Playwright Chromium browser sessions, complemented by programmatic keyboard navigation and ARIA attribute verification suites.

| Metric | Pre-Audit Baseline | Post-Remediation Status | Compliance Target |
| :--- | :--- | :--- | :--- |
| **Total Automated Tests** | 0 | 7 Passed (100%) | 100% Passing |
| **Critical a11y Violations** | 0 | **0** | 0 |
| **Serious a11y Violations** | 2 | **0** | 0 |
| **WCAG 2.1 Level AA Compliance** | Partial (Non-Compliant) | **COMPLIANT (Level AA)** | WCAG 2.1 AA |
| **Keyboard Navigability** | Untested | **Verified (Logical Tab Order)** | 100% Tab Accessible |
| **Status Announcements** | Missing | **Polite Live Region Active** | WCAG 4.1.3 |

---

## 2. Audit Scope & Target Surfaces
The audit targeted all user-facing views, forms, modals, and interactive widgets comprising the two primary workflows:
1. **Lead Detail View (`#lead-view`):** Lead data presentation, identity attributes, financial indicators, and conversion launch button.
2. **Convert Lead Modal Dialog (`#modal-convert`):** Interactive modal dialog with deal configuration fields, policy selectors, and action triggers.
3. **Deal Detail View (`#deal-view`):** Deal summary, linked lead foreign key reference, status indicator badge, and workflow progression controls (`Mark as Won`, `Mark as Lost`).
4. **Deal Lost Modal Dialog (`#modal-lost`):** Reason selection dropdown, conditional mandatory note input, and submission actions.
5. **Toast Notifications (`#toast`):** Asynchronous feedback banners displayed following state transitions.

---

## 3. Discovered Accessibility Violations & Remediations

### 3.1 Violation 1: Color Contrast Ratio Failure (`color-contrast`)
* **Standard:** WCAG 2.1 Success Criterion 1.4.3: Contrast (Minimum) (Level AA)
* **Impact Level:** Serious
* **Affected Elements:**
  - `#btn-mark-won` (`<button class="btn btn-success">Mark as Won</button>`)
  - `#toast.success` (`<div class="toast success">Lead converted successfully!</div>`)
* **Problem Analysis:** The initial styling utilized `#16a34a` (Tailwind green-600) as background against `#ffffff` foreground text with regular font weight (10pt/12pt). Axe-core measured a contrast ratio of **3.29:1**, significantly below the mandatory **4.5:1** ratio required for normal text under WCAG Level AA.
* **Remediation Implemented:**
  - Updated button and notification background color to `#15803d` (Tailwind green-700) and deepened hover states.
  - Calculated Relative Luminance:
    $$L_{bg} = 0.2126 \times 0.0075 + 0.7152 \times 0.2185 + 0.0722 \times 0.0470 \approx 0.1613$$
    $$\text{Contrast Ratio} = \frac{1.0 + 0.05}{0.1613 + 0.05} = \frac{1.05}{0.2113} \approx 4.97:1$$
  - Contrast ratio increased to **4.97:1**, achieving full WCAG 2.1 AA compliance.

### 3.2 Violation 2: Missing Semantic Main Landmark (`landmark-one-main`)
* **Standard:** WCAG 2.1 Guideline 1.3: Adaptable & Guideline 2.4: Navigable
* **Impact Level:** Moderate / Best Practice
* **Affected Element:** `html` root container (`<div class="container" id="app">`)
* **Problem Analysis:** Screen reader users rely on landmark roles (`<main>`, `<nav>`, `<header>`) to bypass repetitive blocks and jump directly to primary content.
* **Remediation Implemented:**
  - Converted the generic top-level wrapper to a semantic landmark element: `<main class="container" id="app" role="main">`.

### 3.3 Usability Enhancement: Screen Reader Status Announcements (WCAG 4.1.3)
* **Standard:** WCAG 2.1 Success Criterion 4.1.3: Status Messages (Level AA)
* **Impact Level:** Usability & Assistive Tech Compatibility
* **Affected Element:** Notification toast container (`#toast`)
* **Remediation Implemented:**
  - Added ARIA live attributes: `<div id="toast" class="toast" role="status" aria-live="polite"></div>`.
  - Ensures assistive technologies immediately announce state transition feedback (e.g., "Lead converted successfully!") to vision-impaired operators without interrupting current focus.

---

## 4. Test Suite Structure & Verification Results

The automated accessibility test suite is implemented in [`tests/team/a11y/test_accessibility_axe.py`](file:///c:/Users/uh723/Downloads/frappe-crm-sqe/tests/team/a11y/test_accessibility_axe.py):

```
tests/team/a11y/
└── test_accessibility_axe.py
    ├── test_accessibility_lead_view                  [PASSED]  (Axe WCAG 2.1 AA rule scan)
    ├── test_accessibility_convert_lead_modal         [PASSED]  (Modal ARIA dialog & form audit)
    ├── test_accessibility_deal_view                  [PASSED]  (Deal interface contrast & landmarks)
    ├── test_accessibility_lost_modal                 [PASSED]  (Dropdown & conditional textarea audit)
    ├── test_keyboard_navigation_and_tab_order        [PASSED]  (Tab traversal & modal focus capture)
    ├── test_aria_form_labels_and_status_announcements[PASSED]  (Explicit form-for associations & live region)
    └── test_interactive_target_sizes_wcag           [PASSED]  (WCAG 2.5.8 target dimensions >=24x24px)
```

### Execution Log Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.1.1, pluggy-1.6.0
plugins: anyio-4.14.2, asyncio-1.4.0, cov-7.1.0, playwright-0.10.0
collected 7 items

tests/team/a11y/test_accessibility_axe.py::test_accessibility_lead_view[chromium] PASSED [ 14%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_convert_lead_modal[chromium] PASSED [ 28%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_deal_view[chromium] PASSED [ 42%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_lost_modal[chromium] PASSED [ 57%]
tests/team/a11y/test_accessibility_axe.py::test_keyboard_navigation_and_tab_order[chromium] PASSED [ 71%]
tests/team/a11y/test_accessibility_axe.py::test_aria_form_labels_and_status_announcements[chromium] PASSED [ 85%]
tests/team/a11y/test_accessibility_axe.py::test_interactive_target_sizes_wcag[chromium] PASSED [100%]

============================== 7 passed in 3.89s ==============================
```

---

## 5. Traceability to Accessibility & Usability Standards

| Requirement / Standard | Rule ID | Audit Method | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **WCAG 1.4.3 (Contrast Minimum)** | `color-contrast` | axe-core automated color sampling | 4.97:1 ratio achieved | **PASSED** |
| **WCAG 1.3.1 (Info and Relationships)** | `label`, `aria-roles` | axe-core + Playwright attribute check | Explicit `for`/`id` bindings | **PASSED** |
| **WCAG 2.1.1 (Keyboard)** | `keyboard` | Playwright sequential tab key traversal | Logical focus sequence | **PASSED** |
| **WCAG 2.1.2 (No Keyboard Trap)** | `escape-key` | Escape key event simulation | Modals dismiss cleanly | **PASSED** |
| **WCAG 2.4.1 (Bypass Blocks)** | `landmark-one-main` | axe-core landmark tree analysis | `<main role="main">` verified | **PASSED** |
| **WCAG 2.5.8 (Target Size Minimum)** | `target-size` | Bounding box geometric calculation | Buttons $\ge 38\text{px} \times 120\text{px}$ | **PASSED** |
| **WCAG 4.1.3 (Status Messages)** | `aria-live` | DOM inspection of `#toast` | `role="status"`, `aria-live="polite"` | **PASSED** |
