"""
API & Integration Test Suite: Deal Status Update Endpoints.
Endpoints:
- PUT /api/resource/CRM Deal/{name}
- POST /api/method/frappe.client.set_value
- GET /api/resource/CRM Deal/{name}
Covers:
- Valid status update
- Transition to Won (automated closed_date & probability)
- Transition to Lost with reasons (BR-02)
- Rejection of missing reason / notes
- Unauthorized status update
- Activity log entry creation
"""

import pytest

import frappe
from tests.team.api.api_client import FrappeAPIClient
from tests.team.fixtures.mock_frappe import set_permission_override, set_user


@pytest.fixture
def client():
    return FrappeAPIClient()


def test_api_deal_status_update_valid(clean_db, client, deal_fact):
    """TC-API-DS-01: Valid status update via REST PUT returns HTTP 200."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_update = client.put(f"/api/resource/CRM Deal/{deal_name}", {"status": "Negotiation"})
    assert res_update.status_code == 200
    assert res_update.json()["data"]["status"] == "Negotiation"


def test_api_deal_transition_to_won(clean_db, client, deal_fact):
    """TC-API-DS-02 / BR-03: Transition to Won populates closed_date and probability."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification", "probability": 0})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_won = client.put(f"/api/resource/CRM Deal/{deal_name}", {"status": "Won", "probability": 0})
    assert res_won.status_code == 200
    deal_data = res_won.json()["data"]
    assert deal_data["status"] == "Won"
    assert deal_data["closed_date"] == frappe.utils.nowdate()
    assert deal_data["probability"] == 100


def test_api_deal_transition_to_lost_valid(clean_db, client, deal_fact):
    """TC-API-DS-03 / BR-02: Transition to Lost with valid reason succeeds."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_lost = client.put(
        f"/api/resource/CRM Deal/{deal_name}",
        {"status": "Lost", "lost_reason": "Price too high"},
    )
    assert res_lost.status_code == 200
    assert res_lost.json()["data"]["status"] == "Lost"


def test_api_deal_transition_to_lost_missing_reason_rejected(clean_db, client, deal_fact):
    """TC-API-DS-04 / BR-02: Transition to Lost without reason returns HTTP 400."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_fail = client.put(f"/api/resource/CRM Deal/{deal_name}", {"status": "Lost", "lost_reason": None})
    assert res_fail.status_code == 400
    assert "Please specify a reason" in res_fail.json()["message"]


def test_api_deal_transition_to_lost_other_missing_notes_rejected(clean_db, client, deal_fact):
    """TC-API-DS-05 / BR-02: Transition to Lost with Other but no notes returns HTTP 400."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_fail = client.put(
        f"/api/resource/CRM Deal/{deal_name}",
        {"status": "Lost", "lost_reason": "Other", "lost_notes": None},
    )
    assert res_fail.status_code == 400
    assert "specify the reason for losing the deal" in res_fail.json()["message"]

    # Now provide notes -> succeeds
    res_success = client.put(
        f"/api/resource/CRM Deal/{deal_name}",
        {"status": "Lost", "lost_reason": "Other", "lost_notes": "Client delayed expansion to next fiscal year"},
    )
    assert res_success.status_code == 200


def test_api_deal_set_value_rpc(clean_db, client, deal_fact):
    """TC-API-DS-06: frappe.client.set_value RPC updates field and records status log."""
    deal_payload = deal_fact.build_synthetic_deal({"status": "Qualification"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    res_rpc = client.post(
        "/api/method/frappe.client.set_value",
        {"doctype": "CRM Deal", "name": deal_name, "fieldname": "status", "value": "Negotiation"},
    )
    assert res_rpc.status_code == 200

    # Retrieve and verify audit log was created
    res_get = client.get(f"/api/resource/CRM Deal/{deal_name}")
    assert res_get.status_code == 200
    logs = res_get.json()["data"].get("status_change_log", [])
    assert len(logs) >= 1


def test_api_unauthorized_deal_update(clean_db, client, deal_fact):
    """TC-API-DS-07: Sales User updating another user's deal returns HTTP 403."""
    deal_payload = deal_fact.build_synthetic_deal({"deal_owner": "rep_a@example.com"})
    res_create = client.post("/api/resource/CRM Deal", deal_payload)
    deal_name = res_create.json()["data"]["name"]

    set_user("rep_b@example.com", ["Sales User"])
    set_permission_override("CRM Deal", "write", deal_name, "rep_b@example.com", False)

    res_update = client.put(f"/api/resource/CRM Deal/{deal_name}", {"status": "Negotiation"})
    assert res_update.status_code == 403
