"""
API & Integration Test Suite: Lead Conversion Endpoints.
Endpoints:
- POST /api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal
- GET /api/resource/CRM Lead/{name}
- GET /api/resource/CRM Deal/{name}
Covers:
- Valid lead conversion
- Ineligible lead conversion (status Lost)
- Unauthorized conversion (PermissionError)
- Missing or invalid input
- Repeated conversion & idempotency policies
- Lead-to-deal relationship verification
- Persisted lead conversion status
"""

import pytest

from tests.team.api.api_client import FrappeAPIClient
from tests.team.fixtures.mock_frappe import set_permission_override, set_user


@pytest.fixture
def client():
    return FrappeAPIClient()


def test_api_valid_lead_conversion(clean_db, client, lead_fact):
    """TC-API-LC-01: Valid Lead conversion returns HTTP 200 and deal name."""
    # Seed lead via REST API
    lead_payload = lead_fact.build_synthetic_lead({
        "first_name": "Benjamin",
        "last_name": "Franklin",
        "email": "ben.franklin@postoffice.gov",
        "organization": "National Postal Service",
    })
    res_lead = client.post("/api/resource/CRM Lead", lead_payload)
    assert res_lead.status_code == 200
    lead_name = res_lead.json()["data"]["name"]

    # Convert Lead to Deal via RPC
    res_conv = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name, "deal": {"deal_value": 75000.0}},
    )
    assert res_conv.status_code == 200
    deal_name = res_conv.json()["message"]
    assert deal_name.startswith("CRM-DEAL-")

    # Verify created Deal via REST
    res_deal = client.get(f"/api/resource/CRM Deal/{deal_name}")
    assert res_deal.status_code == 200
    deal_data = res_deal.json()["data"]
    assert deal_data["lead"] == lead_name
    assert deal_data["deal_value"] == 75000.0

    # Verify Lead persisted conversion status via REST
    res_updated_lead = client.get(f"/api/resource/CRM Lead/{lead_name}")
    assert res_updated_lead.status_code == 200
    assert res_updated_lead.json()["data"]["converted"] == 1
    assert res_updated_lead.json()["data"]["status"] == "Qualified"


def test_api_conversion_ineligible_lost_lead(clean_db, client, lead_fact):
    """TC-API-LC-02: Conversion of Lost lead returns HTTP 400 with ValidationError."""
    lead_payload = lead_fact.build_lost_lead(lost_reason="Competition")
    res_lead = client.post("/api/resource/CRM Lead", lead_payload)
    lead_name = res_lead.json()["data"]["name"]

    res_conv = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name},
    )
    assert res_conv.status_code == 400
    assert "Cannot convert a lead with status" in res_conv.json()["message"]


def test_api_unauthorized_conversion(clean_db, client, lead_fact):
    """TC-API-LC-03: Unauthorized conversion returns HTTP 403."""
    lead_payload = lead_fact.build_synthetic_lead({"lead_owner": "other_agent@example.com"})
    res_lead = client.post("/api/resource/CRM Lead", lead_payload)
    lead_name = res_lead.json()["data"]["name"]

    set_user("rep@example.com", ["Sales User"])
    set_permission_override("CRM Lead", "write", lead_name, "rep@example.com", False)

    res_conv = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name},
    )
    assert res_conv.status_code == 403
    assert "Not allowed to convert Lead to Deal" in res_conv.json()["message"]


def test_api_missing_or_invalid_lead(clean_db, client):
    """TC-API-LC-04: Non-existent or empty lead input returns HTTP 404."""
    res_empty = client.post("/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal", {"lead": ""})
    assert res_empty.status_code == 404

    res_missing = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": "NON-EXISTENT-LEAD-999"},
    )
    assert res_missing.status_code == 404


def test_api_repeated_conversion_policies(clean_db, client, lead_fact):
    """TC-API-LC-05: Repeated conversion with 'Fail' vs. 'Return Existing'."""
    lead_payload = lead_fact.build_synthetic_lead()
    res_lead = client.post("/api/resource/CRM Lead", lead_payload)
    lead_name = res_lead.json()["data"]["name"]

    # Initial conversion
    res_1 = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name},
    )
    deal_1 = res_1.json()["message"]

    # Repeated with Fail policy -> HTTP 400
    res_fail = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name, "if_converted": "Fail"},
    )
    assert res_fail.status_code == 400
    assert "is already converted to Deal" in res_fail.json()["message"]

    # Repeated with Return Existing policy -> HTTP 200, returns deal_1
    res_return = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name, "if_converted": "Return Existing"},
    )
    assert res_return.status_code == 200
    assert res_return.json()["message"] == deal_1
