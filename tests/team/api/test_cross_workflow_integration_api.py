"""
API & Integration Test Suite: Cross-Workflow Integration Pipeline.
Verifies the end-to-end integration between:
1. Workflow 1: Convert Lead to Deal (REST POST Lead -> RPC convert_to_deal)
2. Workflow 2: Update Deal Status (REST PUT Deal Status -> Transition to Won)
3. Shared Relational Integrity: Invariant link deal.lead, persistence, and non-duplication.
"""

import pytest

import frappe
from tests.team.api.api_client import FrappeAPIClient


@pytest.fixture
def client():
    return FrappeAPIClient()


def test_cross_workflow_api_end_to_end_pipeline(clean_db, client, lead_fact):
    """TC-API-SH-01: Cross-workflow integration test combining Workflow 1 and Workflow 2."""
    # -----------------------------------------------------------------------
    # Step 1: Create a synthetic Lead via REST API
    # -----------------------------------------------------------------------
    lead_payload = lead_fact.build_synthetic_lead({
        "first_name": "Eleanor",
        "last_name": "Roosevelt",
        "email": "eleanor@diplomacy.org",
        "organization": "Global Outreach Alliance",
        "annual_revenue": 300000.0,
    })
    res_lead = client.post("/api/resource/CRM Lead", lead_payload)
    assert res_lead.status_code == 200
    lead_id = res_lead.json()["data"]["name"]

    # -----------------------------------------------------------------------
    # Step 2: Convert Lead to Deal via RPC Endpoint (Workflow 1)
    # -----------------------------------------------------------------------
    res_convert = client.post(
        "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
        {"lead": lead_id, "deal": {"deal_value": 85000.0}},
    )
    assert res_convert.status_code == 200
    deal_id = res_convert.json()["message"]
    assert deal_id.startswith("CRM-DEAL-")

    # -----------------------------------------------------------------------
    # Step 3: Retrieve newly created Deal and verify foreign key link
    # -----------------------------------------------------------------------
    res_deal = client.get(f"/api/resource/CRM Deal/{deal_id}")
    assert res_deal.status_code == 200
    deal_data = res_deal.json()["data"]
    assert deal_data["lead"] == lead_id
    assert deal_data["deal_value"] == 85000.0

    # -----------------------------------------------------------------------
    # Step 4: Advance Deal through status lifecycle (Workflow 2)
    # -----------------------------------------------------------------------
    # Move to Negotiation
    res_step1 = client.put(f"/api/resource/CRM Deal/{deal_id}", {"status": "Negotiation"})
    assert res_step1.status_code == 200
    assert res_step1.json()["data"]["status"] == "Negotiation"

    # Move to Won (triggers BR-03 automated closure date)
    res_step2 = client.put(f"/api/resource/CRM Deal/{deal_id}", {"status": "Won", "probability": 0})
    assert res_step2.status_code == 200
    won_data = res_step2.json()["data"]
    assert won_data["status"] == "Won"
    assert won_data["closed_date"] == frappe.utils.nowdate()

    # -----------------------------------------------------------------------
    # Step 5: Verify Shared Data Consistency & Relational Invariance
    # -----------------------------------------------------------------------
    # Verify deal still maintains valid lead link
    res_final_deal = client.get(f"/api/resource/CRM Deal/{deal_id}")
    assert res_final_deal.status_code == 200
    assert res_final_deal.json()["data"]["lead"] == lead_id

    # Verify original lead record persisted cleanly and is not duplicated
    res_final_lead = client.get(f"/api/resource/CRM Lead/{lead_id}")
    assert res_final_lead.status_code == 200
    lead_data = res_final_lead.json()["data"]
    assert lead_data["converted"] == 1
    assert lead_data["status"] == "Qualified"

    # Verify database contains exactly 1 lead and 1 deal for this conversion
    assert len(clean_db.get_all("CRM Lead", {"name": lead_id})) == 1
    assert len(clean_db.get_all("CRM Deal", {"lead": lead_id})) == 1
