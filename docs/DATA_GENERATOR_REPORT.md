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
- Overall test suite now comprises **107 tests passing with zero failures**.

---

## 6. Constraint Mutation & Regeneration Demonstration

In compliance with project requirements (*"Modify at least two constraints, regenerate the test data, and demonstrate the change; expect an updated spec in the viva"*), the generator was subjected to dynamic constraint modification:

### 6.1 Baseline vs. Modified Constraints Specification

| Field Name | Baseline OpenAPI Constraint | Modified Constraint | Engineering Rationale | Effect on Generated Triples |
| :--- | :--- | :--- | :--- | :--- |
| **`deal_value`** | `minimum: 0.00` | `minimum: 50.00` | Enterprise policy establishing minimum deal transaction size. | **Baseline Triple:** `[-0.01, 0.00, 0.01]`<br>**Modified Triple:** `[49.99, 50.00, 50.01]` |
| **`probability`** | `maximum: 100.0` | `maximum: 1.00` | Decimal probability standard ($[0.0, 1.0]$ instead of percentage $[0, 100]$). | **Baseline Triple:** `[99.9, 100.0, 100.1]`<br>**Modified Triple:** `[0.99, 1.00, 1.01]` |

### 6.2 Regeneration Execution & JSON Diff Verification

When `docs/openapi_crm.yaml` is updated with the modified constraints and `python tests/team/generator/data_generator.py` is re-executed:

```json
// BEFORE: Baseline Generated Currency BVA (docs/openapi_crm.yaml with min=0.0)
"bva_currency": [
  {"point_type": "below_min", "value": -0.01, "expected_valid": false},
  {"point_type": "exact_min", "value": 0.0,   "expected_valid": true},
  {"point_type": "above_min", "value": 0.01,  "expected_valid": true}
]

// AFTER: Regenerated Currency BVA (docs/openapi_crm.yaml with min=50.0)
"bva_currency": [
  {"point_type": "below_min", "value": 49.99, "expected_valid": false},
  {"point_type": "exact_min", "value": 50.0,  "expected_valid": true},
  {"point_type": "above_min", "value": 50.01, "expected_valid": true}
]
```

### 6.3 Viva Voce Live Demonstration Procedure
1. Open `docs/openapi_crm.yaml`.
2. Modify `minimum: 0.0` under `CRMDealInput.deal_value` to `minimum: 50.0`.
3. Run `python tests/team/generator/data_generator.py`.
4. Run `pytest tests/team/generator/test_generated_data.py -v`.
5. Observe that previous boundary test cases (e.g. testing `0.00` or `10.00`) now fail as invalid, proving that the test suite is strictly coupled to the generated schema data.
6. Revert change back to `minimum: 0.0` and regenerate to restore green pass.
