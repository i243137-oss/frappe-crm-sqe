# Accessibility (a11y) & Usability WCAG 2.1 AA & Lighthouse Audit Report

## 1. Executive Summary
As part of the SE3002 Software Quality Engineering (SQE) project on **Frappe CRM**, an end-to-end accessibility and usability audit was performed on the core **Lead Conversion** and **Deal Status Progression** interfaces.

The evaluation rigorously validates compliance with:
- **Web Content Accessibility Guidelines (WCAG) 2.1 Level A & Level AA**
- **Google Lighthouse Standards** (Accessibility, Best Practices, SEO)
- **Section 508 & EN 301 549 Accessibility Specifications**

Testing integrated three complementary testing engines:
1. **Playwright Chromium**: Automated keyboard navigation, logical focus trapping, and interactive control sizing.
2. **axe-core (v4.12)**: Automated DOM rule engine scanning contrast, landmarks, ARIA associations, and form roles.
3. **Google Lighthouse (v13.6.0)**: Production-grade headless browser audit generating quantitative category scores.

---

## 2. Before-and-After Remediation Comparison

A critical usability and accessibility defect was diagnosed on the Deal Screen and notification components. Below is the systematic before-and-after evaluation:

| Audit Dimension | Before Remediation | After Remediation | WCAG 2.1 / Quality Benchmark | Status |
| :--- | :---: | :---: | :---: | :---: |
| **`#btn-mark-won` Contrast Ratio** | **3.29:1** (FAIL) | **4.97:1** (PASS) | Minimum 4.5:1 (Normal Text) | **Remediated** |
| **`#toast.success` Contrast Ratio** | **3.29:1** (FAIL) | **4.97:1** (PASS) | Minimum 4.5:1 (Normal Text) | **Remediated** |
| **Semantic Main Landmark** | Generic `<div>` (Missing) | `<main role="main">` | Landmark navigation requirement | **Remediated** |
| **Live Region Status Feedback** | None (Silent) | `role="status" aria-live="polite"` | WCAG 4.1.3 (Status Messages) | **Remediated** |
| **Viewport & Mobile Metadata** | None | `<meta name="viewport">` | Mobile responsiveness & usability | **Remediated** |
| **SEO Meta Description** | None | Valid meta description | Discoverability & crawling | **Remediated** |
| **Axe Serious Violations** | **2** | **0** | Zero critical/serious defects | **PASSED** |
| **Lead Screen Lighthouse a11y** | 89 / 100 | **100 / 100** | 100% Accessibility Score | **PASSED** |
| **Deal Screen Lighthouse a11y** | 86 / 100 | **100 / 100** | 100% Accessibility Score | **PASSED** |

---

## 3. Google Lighthouse Quantitative Audit Results

Lighthouse audits were executed in headless Chrome against both primary application workflows:
- **Lead Screen (`/`)**: Conversion trigger, lead attributes, modal dialog.
- **Deal Screen (`/deal`)**: Status progression, opportunity valuation, lost reason workflow.

```text
==================================================
LIGHTHOUSE AUDIT SUMMARY SCORES
==================================================

Lead Screen:
  - Accessibility: 100 / 100 (Perfect Compliance)
  - Best Practices: 96 / 100
  - SEO: 100 / 100

Deal Screen:
  - Accessibility: 100 / 100 (Perfect Compliance)
  - Best Practices: 96 / 100
  - SEO: 100 / 100
==================================================
```

### Generated Artifacts
- **Lead Screen Report (HTML)**: [`docs/lighthouse/lead_screen.report.html`](docs/lighthouse/lead_screen.report.html)
- **Lead Screen Report (JSON)**: [`docs/lighthouse/lead_screen.report.json`](docs/lighthouse/lead_screen.report.json)
- **Deal Screen Report (HTML)**: [`docs/lighthouse/deal_screen.report.html`](docs/lighthouse/deal_screen.report.html)
- **Deal Screen Report (JSON)**: [`docs/lighthouse/deal_screen.report.json`](docs/lighthouse/deal_screen.report.json)
- **Summary JSON**: [`docs/lighthouse/lighthouse_summary.json`](docs/lighthouse/lighthouse_summary.json)

---

## 4. In-Depth Technical Defect Analysis & Fixes

### 4.1 Mathematical Contrast Derivation (WCAG 1.4.3)
The contrast ratio $C$ between relative luminance of text $L_1$ and background $L_2$ (where $L_1 > L_2$) is defined by:
$$C = \frac{L_1 + 0.05}{L_2 + 0.05}$$

* **Initial Defect**: Foreground `#ffffff` ($L_1 = 1.0$) against background `#16a34a` (sRGB: 22, 163, 74):
  $$R_{lin} = 0.0084, \quad G_{lin} = 0.3686, \quad B_{lin} = 0.0694$$
  $$L_2 = 0.2126(0.0084) + 0.7152(0.3686) + 0.0722(0.0694) \approx 0.2687$$
  $$C = \frac{1.0 + 0.05}{0.2687 + 0.05} = \frac{1.05}{0.3187} \approx 3.29:1 \quad (\text{FAILS } \ge 4.5:1)$$

* **Remediated Style**: Deepened to `#15803d` (sRGB: 21, 128, 61):
  $$L_2 \approx 0.1613 \implies C = \frac{1.05}{0.1613 + 0.05} = \frac{1.05}{0.2113} \approx 4.97:1 \quad (\text{PASSES } \ge 4.5:1)$$

---

## 5. Automated Playwright & Axe Test Suite

The automated verification suite in [`tests/team/a11y/test_accessibility_axe.py`](tests/team/a11y/test_accessibility_axe.py) executes 7 test specifications:

1. `test_accessibility_lead_view`: Verifies zero critical/serious axe-core violations on the primary lead view.
2. `test_accessibility_convert_lead_modal`: Verifies modal dialog `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` bindings.
3. `test_accessibility_deal_view`: Audits contrast and landmark containment on the deal lifecycle interface.
4. `test_accessibility_lost_modal`: Audits conditional reason inputs and form accessibility under lost state transitions.
5. `test_keyboard_navigation_and_tab_order`: Simulates Tab key navigation ensuring immediate focus capture upon modal launch (`#input-deal-name`) and logical cyclic tab order.
6. `test_aria_form_labels_and_status_announcements`: Asserts explicit `label[for]` associations and polite ARIA live notifications.
7. `test_interactive_target_sizes_wcag`: Asserts touch and click targets satisfy WCAG 2.5.8 minimum bounding dimensions ($\ge 24\text{px} \times 24\text{px}$).

### Test Execution Proof
```text
tests/team/a11y/test_accessibility_axe.py::test_accessibility_lead_view[chromium] PASSED [ 14%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_convert_lead_modal[chromium] PASSED [ 28%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_deal_view[chromium] PASSED [ 42%]
tests/team/a11y/test_accessibility_axe.py::test_accessibility_lost_modal[chromium] PASSED [ 57%]
tests/team/a11y/test_accessibility_axe.py::test_keyboard_navigation_and_tab_order[chromium] PASSED [ 71%]
tests/team/a11y/test_accessibility_axe.py::test_aria_form_labels_and_status_announcements[chromium] PASSED [ 85%]
tests/team/a11y/test_accessibility_axe.py::test_interactive_target_sizes_wcag[chromium] PASSED [100%]

============================== 7 passed in 3.89s ==============================
```
