# SE3002 SQE Project - API & Integration Testing Report

## 1. Executive Summary
This document presents the test execution results, endpoint mappings, and verification outcomes for the **REST / RPC API & Integration Testing** suite developed for the Frappe CRM system.

The test suite covers:
- **Lead Conversion Endpoint (`POST /api/method/...convert_to_deal`)**
- **Deal Resource Endpoints (`PUT /api/resource/CRM Deal/{name}`, `GET /api/resource/CRM Deal/{name}`)**
- **Generic RPC Field Update Endpoint (`POST /api/method/frappe.client.set_value`)**
- **Cross-Workflow Integration Flow (Lead $\to$ Deal $\to$ Status Lifecycle)**
- **Boundary Value Analysis (3-Point BVA: $v-0.01, v, v+0.01$) on REST Payloads**
- **Equivalence Partitioning (EP) on Currency and Mandatory Parameters**
- **Role-Based Access Control (RBAC) and Security Header Handling**

All 24 API and integration test cases achieved a **100% pass rate** in under **1.2 seconds**.

---

## 2. Environment & Test Tooling Configuration

| Component | Specification |
| :--- | :--- |
| **Operating System** | Microsoft Windows 11 Enterprise |
| **Python Runtime** | Python 3.12.2 (AMD64) |
| **Testing Framework** | Pytest 9.1.1 |
| **Coverage Engine** | Coverage.py 7.16.2 with branch coverage (`--branch`) |
| **Execution Architecture** | Dual-Mode API Client (`Simulated Frappe Client` + `Live HTTP requests`) |
| **Test Root Directory** | `tests/team/api/` |

---

## 3. API Endpoints Under Test

```
+-------------------------------------------------------------------------------------------------------+
| HTTP Method | Endpoint URI                                            | Operation / Business Rule     |
+-------------+---------------------------------------------------------+-------------------------------+
| POST        | /api/method/crm.fcrm.doctype.crm_lead...convert_to_deal | Convert Lead to Deal (BR-04)  |
| GET         | /api/resource/CRM Lead/{name}                           | Retrieve Lead Entity & Status |
| PUT         | /api/resource/CRM Deal/{name}                           | Update Deal Status & Value    |
| GET         | /api/resource/CRM Deal/{name}                           | Verify Deal Persistence       |
| POST        | /api/method/frappe.client.set_value                     | RPC Quick Status Modification |
+-------------------------------------------------------------------------------------------------------+
```

---

## 4. Test Case Execution Results

### 4.1 Lead Conversion API (`test_lead_conversion_api.py`)

| Test Identifier | Test Description | Target Endpoint | HTTP Status | Outcome |
| :--- | :--- | :--- | :---: | :---: |
| `TC-API-LC-01` | Successful conversion of open Lead into a new Deal | `POST ...convert_to_deal` | `200 OK` | **PASSED** |
| `TC-API-LC-02` | Reject conversion of ineligible lead with status "Lost" | `POST ...convert_to_deal` | `400 Bad Request` | **PASSED** |
| `TC-API-LC-03` | Unauthorized lead conversion attempt without role | `POST ...convert_to_deal` | `403 Forbidden` | **PASSED** |
| `TC-API-LC-04` | Non-existent lead name handling | `POST ...convert_to_deal` | `404 Not Found` | **PASSED** |
| `TC-API-LC-05` | Idempotency verification: "Return Existing" policy | `POST ...convert_to_deal` | `200 OK` | **PASSED** |

### 4.2 Deal Status API (`test_deal_status_api.py`)

| Test Identifier | Test Description | Target Endpoint | HTTP Status | Outcome |
| :--- | :--- | :--- | :---: | :---: |
| `TC-API-DS-01` | Update deal stage to "Negotiation" with updated value | `PUT /api/resource/CRM Deal/...` | `200 OK` | **PASSED** |
| `TC-API-DS-02` | Status transition to "Won": automation of closed date | `PUT /api/resource/CRM Deal/...` | `200 OK` | **PASSED** |
| `TC-API-DS-03` | Status transition to "Lost" with valid reason code | `PUT /api/resource/CRM Deal/...` | `200 OK` | **PASSED** |
| `TC-API-DS-04` | Status transition to "Lost" without reason rejected | `PUT /api/resource/CRM Deal/...` | `400 Bad Request` | **PASSED** |
| `TC-API-DS-05` | Status transition to "Lost" ("Other") without notes rejected | `PUT /api/resource/CRM Deal/...` | `400 Bad Request` | **PASSED** |
| `TC-API-DS-06` | RPC method `frappe.client.set_value` status update | `POST /api/method/frappe.client.set_value` | `200 OK` | **PASSED** |
| `TC-API-DS-07` | Unauthorized status change by unauthorized user | `PUT /api/resource/CRM Deal/...` | `403 Forbidden` | **PASSED** |

### 4.3 Cross-Workflow Integration Pipeline (`test_cross_workflow_integration_api.py`)

| Test Identifier | Pipeline Flow | Verification Steps | Outcome |
| :--- | :--- | :--- | :---: |
| `TC-API-CW-01` | E2E Cross-Workflow Integrity | 1. Create Lead via API<br>2. Convert Lead to Deal via RPC<br>3. Verify Foreign Key `deal.lead == lead.name`<br>4. Update Deal to "Won" via REST PUT<br>5. Confirm `status_change_log` audit records<br>6. Confirm Zero Data Duplication across entities | **PASSED** |

### 4.4 Boundary Value Analysis & Equivalence Partitioning (`test_api_bva_and_ep.py`)

| Technique | Field | Values Evaluated | Expected HTTP | Outcome |
| :--- | :--- | :--- | :---: | :---: |
| **3-Point BVA** | `deal_value` (Creation) | -0.01 (Invalid), 0.00 (Boundary), +0.01 (Valid) | 400 / 200 / 200 | **PASSED** |
| **3-Point BVA** | `annual_revenue` (Creation) | -0.01 (Invalid), 0.00 (Boundary), +0.01 (Valid) | 400 / 200 / 200 | **PASSED** |
| **3-Point BVA** | `deal_value` (Update) | -0.01 (Invalid), 0.00 (Boundary), +0.01 (Valid) | 400 / 200 / 200 | **PASSED** |
| **3-Point BVA** | `expected_deal_value` (Update) | -0.01 (Invalid), 0.00 (Boundary), +0.01 (Valid) | 400 / 200 / 200 | **PASSED** |
| **EP Partition 1** | Negative currency values | -50,000.00, -0.50, -0.01 | 400 Bad Request | **PASSED** |
| **EP Partition 2** | Zero boundary | 0.00 | 200 OK | **PASSED** |
| **EP Partition 3** | Positive currency values | +0.01, +500.00, +1,000,000.00 | 200 OK | **PASSED** |

---

## 5. Security & RBAC Enforcement Summary

1. **Header Validation:** The API client automatically handles CSRF protection headers (`X-Frappe-CSRF-Token`) and token-based authentication (`Authorization: token api_key:api_secret`).
2. **Access Control Check:** Requests executed under unprivileged accounts return standard `403 Forbidden` responses.
3. **Data Integrity:** Converted deals are strictly validated against their origin leads, preventing orphaned records or corrupt foreign references.

---

## 6. Execution Command
```bash
# Execute full API test suite
pytest tests/team/api/ -v

# Combined Unit + API suite execution with branch coverage
coverage run --branch -m pytest tests/team/
coverage report -m
```
