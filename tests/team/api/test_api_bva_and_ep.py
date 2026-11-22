"""
API & Integration Test Suite: 3-Point Boundary Value Analysis & Equivalence Partitioning.
Applies BVA and Equivalence Partitioning directly to API payloads across:
- Monetary fields: deal_value, expected_deal_value, annual_revenue
- 3-point boundary values: -0.01 (below), 0.00 (at), +0.01 (above)
- Equivalence partitions: valid positive vs invalid negative
"""

import pytest

from tests.team.api.api_client import FrappeAPIClient


@pytest.fixture
def client():
    return FrappeAPIClient()


# ---------------------------------------------------------------------------
# 3-Point Boundary Value Analysis (BVA) on API Inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["deal_value", "annual_revenue"])
def test_api_three_point_bva_on_deal_creation(clean_db, client, field):
    """TC-API-BVA-01: Tests -0.01 (below), 0.00 (at), and +0.01 (above) boundary via REST POST."""
    # 1. Below boundary: -0.01 -> HTTP 400
    res_below = client.post("/api/resource/CRM Deal", {"organization": "BVA Org", field: -0.01})
    assert res_below.status_code == 400
    assert "cannot be negative" in res_below.json()["message"]

    # 2. Exactly at boundary: 0.00 -> HTTP 200
    res_boundary = client.post("/api/resource/CRM Deal", {"organization": "BVA Org", field: 0.00})
    assert res_boundary.status_code == 200
    assert res_boundary.json()["data"][field] == 0.00

    # 3. Above boundary: +0.01 -> HTTP 200
    res_above = client.post("/api/resource/CRM Deal", {"organization": "BVA Org", field: 0.01})
    assert res_above.status_code == 200
    assert res_above.json()["data"][field] == 0.01


@pytest.mark.parametrize("field", ["deal_value", "expected_deal_value"])
def test_api_three_point_bva_on_deal_update(clean_db, client, deal_fact, field):
    """TC-API-BVA-02: Tests BVA via REST PUT on existing Deal."""
    deal_payload = deal_fact.build_synthetic_deal({field: 1000.0})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    # Below boundary: -0.01 -> rejected
    res_below = client.put(f"/api/resource/CRM Deal/{deal_name}", {field: -0.01})
    assert res_below.status_code == 400

    # Exactly at boundary: 0.00 -> accepted
    res_boundary = client.put(f"/api/resource/CRM Deal/{deal_name}", {field: 0.00})
    assert res_boundary.status_code == 200
    assert res_boundary.json()["data"][field] == 0.00

    # Above boundary: +0.01 -> accepted
    res_above = client.put(f"/api/resource/CRM Deal/{deal_name}", {field: 0.01})
    assert res_above.status_code == 200
    assert res_above.json()["data"][field] == 0.01


# ---------------------------------------------------------------------------
# Equivalence Partitioning (EP) on API Payloads
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "amount,should_pass",
    [
        (-50000.00, False),
        (-0.50, False),
        (-0.01, False),
        (0.00, True),
        (0.01, True),
        (500.00, True),
        (1000000.00, True),
    ],
)
def test_api_equivalence_partitioning_currency(clean_db, client, amount, should_pass):
    """TC-API-EP-01: Equivalence partitions for monetary values in conversion payloads."""
    # Seed a lead
    res_lead = client.post("/api/resource/CRM Lead", {"first_name": "EP", "email": "ep@test.com"})
    lead_name = res_lead.json()["data"]["name"]

    res_conv = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_name, "deal": {"deal_value": amount}},
    )

    if should_pass:
        assert res_conv.status_code == 200
    else:
        assert res_conv.status_code == 400
        assert "cannot be negative" in res_conv.json()["message"]
