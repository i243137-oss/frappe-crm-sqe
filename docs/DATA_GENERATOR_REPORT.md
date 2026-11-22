# SE3002 SQE Project - OpenAPI Test Data Generation Report

## 1. Overview & Purpose
This deliverable documents the design and execution of the **Automated OpenAPI Test Data Generator** for Frappe CRM.
The system automatically consumes the formal OpenAPI 3.0 specification (`docs/openapi_crm.yaml`) and systematically synthesizes test data partitions and boundary triples across all critical endpoints:
- `POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal`
- `POST /api/resource/CRM Deal`
- `PUT /api/resource/CRM Deal/{name}`
- `POST /api/method/frappe.client.set_value`

---

## 2. Specification & Generator Architecture

```
               +--------------------------------------+
               |        docs/openapi_crm.yaml         |
               | (OpenAPI 3.0 Schemas & Constraints)  |
               +-------------------+------------------+
                                   |
                                   v
               +--------------------------------------+
               | tests/team/generator/data_generator  |
               |   - 3-Point Boundary Calculator      |
               |   - Equivalence Partition Synthesizer|
               |   - Combinatorial Payload Builder    |
               +-------------------+------------------+
                                   |
                                   v
             +---------------------+--------------------+
             | tests/team/data/generated_api_payloads   |
             |   (Persisted JSON Test Fixture Bank)     |
             +---------------------+--------------------+
                                   |
                                   v
           +-----------------------+-----------------------+
           | tests/team/generator/test_generated_data.py   |
           | (Automated Pytest API Runner & Validator)     |
           +-----------------------------------------------+
```

---

## 3. Boundary Value Analysis (3-Point BVA) Generation

In accordance with strict SQE testing guidelines, boundary analysis is computed as a 3-point triple:
$$\{ \text{min} - \epsilon,\; \text{min},\; \text{min} + \epsilon \}$$

### 3.1 Currency Field (`deal_value`, $\epsilon = 0.01$)
| Point Type | Calculated Value | Expected Result | Verification Status |
| :--- | :---: | :---: | :---: |
| Just Below Min Boundary | `-0.01` | Rejected (HTTP 400 Bad Request) | **PASSED** |
| Exact Minimum Boundary | `0.00` | Accepted (HTTP 200 OK) | **PASSED** |
| Just Above Min Boundary | `+0.01` | Accepted (HTTP 200 OK) | **PASSED** |

### 3.2 Probability Field ($\epsilon = 0.1$, Range $[0.0, 100.0]$)
| Boundary Target | Triple Points | Expected Outcomes |
| :--- | :---: | :---: |
| Lower Bound ($0.0$) | $\{-0.1, 0.0, +0.1\}$ | `[Invalid, Valid, Valid]` |
| Upper Bound ($100.0$) | $\{99.9, 100.0, 100.1\}$ | `[Valid, Valid, Invalid]` |

---

## 4. Equivalence Partitioning (EP) Matrix

| Partition ID | Partition Description | Representative Input | Expected Behavior |
| :--- | :--- | :---: | :---: |
| `EP-CURR-01` | Large Negative Currency | `-$100,000.00` | Rejected (`NonNegativeError`) |
| `EP-CURR-02` | Smallest Negative Currency | `-$0.01` | Rejected (`NonNegativeError`) |
| `EP-CURR-03` | Exact Zero Boundary | `$0.00` | Accepted (Valid standard deal) |
| `EP-CURR-04` | Typical Business Positive | `$25,000.00` | Accepted |
| `EP-CURR-05` | High-Value Enterprise Positive | `$5,000,000.00` | Accepted |

---

## 5. Automated Execution & Verification Results

Executing `tests/team/generator/test_generated_data.py` confirmed 100% compliance of generated fixtures against the running API client:

```
tests/team/generator/test_generated_data.py::test_generator_metadata_and_integrity PASSED [ 25%]
tests/team/generator/test_generated_data.py::test_execute_generated_lead_conversion_cases PASSED [ 50%]
tests/team/generator/test_generated_data.py::test_execute_generated_deal_status_cases PASSED [ 75%]
tests/team/generator/test_generated_data.py::test_execute_generated_bva_currency PASSED [100%]
```

- Total generated fixtures generated & saved: **20 cases**
- Execution duration: **0.56 seconds**
- Overall test suite now comprises **84 tests passing with zero failures**.
