# SE3002 Software Quality Engineering – Record of Generative AI Tool Use

**System Under Test:** Frappe CRM  
**Target Module:** Leads and Deals  
**Document Reference:** `docs/AI_USE_RECORD.md`  
**CLO Mapping:** CLO1 (Viva, Live Task & AI-Use Record – 20 Marks)  
**Student Contributors & Group Members:**  
- **Umair Hassan**
- **Abdullah**
- **Muhammad Anas**  

---

## 1. Academic Integrity Statement & Disclosure Policy

In strict compliance with Section 7 (*AI use and plagiarism*) of the SE3002 Software Quality Engineering course specification, this document maintains a complete, transparent, and auditable record of all Generative AI tool assistance utilized throughout the project lifecycle.

Every team member has personally reviewed, verified, and empirically executed all generated code, configurations, test suites, and documentation. No fabricated, synthetic, or unverified claims exist in this repository. All test executions, coverage metrics, and mutation scores reported in `docs/` reflect empirical measurements obtained on the local machine and validated in GitHub Actions CI pipelines.

---

## 2. Generative AI Tool Registry

* **Primary AI Assistant:** Antigravity (Google DeepMind Gemini 2.5 / Pro reasoning engine)
* **Execution Interface:** Interactive local agent terminal workspace with sandboxed tool invocation
* **Primary Activities Assisted:** Test scaffold generation, Markdown documentation templating, Mermaid architectural diagram synthesis, AST mutation operator drafting, and mathematical truth table formatting.

---

## 3. Comprehensive AI Usage & Verification Log

| Milestone / Task | Tool Used | Actual Prompt Issued | Model Output Generated | Verification & Fact-Checking Performed | Corrections & Changes Made by Team |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **Milestone 1: Codebase Discovery** | Antigravity (Gemini) | *"Analyze the cloned Frappe CRM codebase under crm/crm/fcrm to identify the DocType definitions and Python methods for converting a Lead into a Deal and updating Deal statuses."* | Suggested standard ERPNext endpoints (`crm.lead.make_deal`). | Cross-checked actual Frappe CRM repository files on disk (`crm/crm/fcrm/`). | **Corrected:** Rejected ERPNext endpoints; replaced with actual Frappe CRM path `crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal` and DocType `CRM Deal`. |
| **Milestone 2: Requirements & Business Rules** | Antigravity (Gemini) | *"Derive a formal Boolean truth table and MC/DC condition pairs for the validate_lost_reason method in crm_deal.py covering conditions status=='Lost', lost_reason present, lost_reason=='Other', and lost_notes present."* | Generated standard 16-row ($2^4$) Boolean truth table. | Checked against AST of `crm_deal.py:285-296`. Identified that Condition C and D only evaluate when $C_A$ and $C_B$ are True. | **Corrected:** Compacted unreachable branches into a mathematically sound 10-row truth table; derived 4 pure MC/DC independent pairs. |
| **Milestone 3: Test Infrastructure Harness** | Antigravity (Gemini) | *"Create a lightweight MockDatabase and DocType controller in tests/team/fixtures/mock_frappe.py that executes real crm_deal.py and crm_lead.py logic without requiring a live MariaDB instance."* | Provided a basic mock dictionary class with dummy `save()` and `insert()`. | Ran against `CRMDeal` and `CRMLead`. Discovered missing lifecycle hooks (`before_validate`, `validate_values`). | **Enhanced:** Added schema-level `non_negative: 1` validation into `mock_frappe.Document.validate_values()`, matching upstream Frappe behavior. |
| **Milestone 4: White-Box Unit Testing** | Antigravity (Gemini) | *"Generate pytest parameterized test fixtures for 3-point Boundary Value Analysis on currency fields (deal_value, expected_deal_value, annual_revenue) testing -0.01, 0.00, and +0.01."* | Drafted `test_business_rules_and_boundaries.py` with mock `frappe.throw()` calls. | Audited test execution; detected that currency test was testing its own `throw` rather than `deal.save()`. | **Corrected:** Refactored tests to invoke `deal.save()` directly so that schema validation in the Document controller is genuinely tested. |
| **Milestone 5: OpenAPI Data Generator** | Antigravity (Gemini) | *"Draft an OpenAPI 3.0 specification covering /api/method/...convert_to_deal, /api/resource/CRM Lead, and /api/resource/CRM Deal with non-negative constraints and valid status enums."* | Generated basic OpenAPI spec with minimum currency constraints. | Validated schema against Frappe CRM JSON schemas (`crm_deal.json`, `crm_lead.json`). | **Enhanced:** Added strict boundary constraints (`minimum: 0.0`), enum fields for Deal Status (`"Qualification"`, `"Won"`, `"Lost"`, etc.), and built dynamic Python generator. |
| **Milestone 6: Playwright E2E Automation** | Antigravity (Gemini) | *"Scaffold a Playwright browser test suite covering the happy path lead conversion, alternative lost reason flows, and keyboard navigation modal dismissal."* | Provided standard Playwright script targeting a live bench server. | Bench server required extensive external Redis and MariaDB daemons. | **Corrected:** Developed standalone lightweight test application server ([`mock_server.py`](tests/team/e2e/mock_server.py)) rendering exact UI components, with native dropdown lead switching and keyboard Enter submission. |
| **Milestone 7: Mutation Testing Engine** | Antigravity (Gemini) | *"Design an AST and token replacement mutation runner for Frappe CRM that injects boundary, arithmetic, and logical mutations into crm_deal.py and crm_lead.py and computes the mutation score."* | Drafted `mutation_runner.py` with 16 mutant specifications targeting real Frappe CRM code. | Verified against real DocTypes; verified that all 16 mutants target executable logic in `crm_deal.py` and `crm_lead.py`. | **Enhanced:** Added automated exit code checking (`sys.exit(1)` on surviving mutants) to enforce strict CI merge blocking, achieving **100% genuine kill score (16/16)**. |
| **Milestone 8: Usability & Accessibility** | Antigravity (Gemini) | *"Analyze axe-core WCAG 2.1 AA audit output for contrast ratio violations on the Mark as Won button and suggest compliant color values."* | Recommended darkening the green button background to `#15803d`. | Verified luminance formula $L = 0.2126R + 0.7152G + 0.0722B$ and contrast ratio $\frac{L_1 + 0.05}{L_2 + 0.05}$. | **Verified:** New color `#15803d` on white yielded 4.97:1 ratio ($\ge 4.5:1$ requirement); confirmed 100/100 score in Google Lighthouse. |
| **Milestone 9: Performance Benchmarking** | Antigravity (Gemini) | *"Draft a Grafana k6 OSS performance benchmark script testing POST /api/method/...convert_to_deal across 1 VU and 5 concurrent VUs with p95 < 300ms SLA."* | Drafted `k6_lead_conversion.js` with random payload generator. | Executed k6 across 1 VU and 5 VUs for sustained 60 seconds each. | **Verified:** Parsed raw JSON metrics (`k6_benchmark_summary.json`); verified $p95$ response times (1.60ms – 4.36ms) and 0% failures against tiered thresholds. |
| **Milestone 10: Defect RCA & CAPA** | Antigravity (Gemini) | *"Format an Ishikawa fishbone diagram and 5 Whys root cause analysis for the four defects identified during test execution."* | Generated initial Fishbone outline for concurrency and contrast issues. | Reviewed against logged defect history (`DEF-01` through `DEF-04`) and Risk Register. | **Validated:** Verified causal connections between root causes, CAPA actions, and verified regression test scripts. |

---

## 4. Viva Voce Defense Commitment

Every member of this project group:
1. Understands every line of source code, test logic, fixture implementation, and configuration file in `tests/team/`, `docs/`, and `.github/`.
2. Is fully prepared to rerun any selected test on demand during the viva examination and explain its exact assertions.
3. Is prepared to receive an unannounced live business-rule or OpenAPI specification change, predict pipeline failures, implement the change, and demonstrate the quality gate response.
4. Affirms that all reported data is truthful, reproducible, and verifiable on disk.
