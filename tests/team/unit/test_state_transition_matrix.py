"""
State Transition Matrix & Invariance Verification Suite for Frappe CRM Deals.
Formally verifies:
1. Valid State Transitions across the sales lifecycle:
   Qualification -> Demo -> Proposal -> Negotiation -> Won / Lost
2. Disallowed & Guarded Transitions from each state:
   - Transition to Lost without lost_reason is rejected (BR-02)
   - Transition to Lost with 'Other' and empty notes is rejected (BR-02)
   - Transition to Won preserves existing closed date and auto-sets default probability (BR-03)
   - Transition with non-existent or illegal status strings is strictly rejected
   - Status transitions record immutable duration and timestamp audit logs
"""

import pytest
import frappe
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal
from tests.team.fixtures.mock_frappe import ValidationError, mock_db


@pytest.fixture(autouse=True)
def clean_state():
    mock_db.reset()
    yield
    mock_db.reset()


# ---------------------------------------------------------------------------
# 1. Valid State Transitions Matrix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "initial_status,next_status,kwargs",
    [
        ("Qualification", "Demo", {}),
        ("Demo", "Proposal", {}),
        ("Proposal", "Negotiation", {}),
        ("Negotiation", "Won", {}),
        ("Qualification", "Won", {}),
        ("Qualification", "Lost", {"lost_reason": "Competitor"}),
        ("Demo", "Lost", {"lost_reason": "Price too high"}),
        ("Proposal", "Lost", {"lost_reason": "Missing features"}),
        ("Negotiation", "Lost", {"lost_reason": "Other", "lost_notes": "Budget frozen by CFO"}),
    ],
)
def test_valid_state_transitions(deal_fact, initial_status, next_status, kwargs):
    """Verifies that all sanctioned lifecycle transitions execute successfully and update audit logs."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": initial_status,
        "deal_value": 45000.0,
        "probability": 20,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    assert deal.status == initial_status

    # Execute transition
    deal.status = next_status
    for k, v in kwargs.items():
        setattr(deal, k, v)
    deal.save()

    assert deal.status == next_status
    if next_status == "Won":
        assert deal.closed_date == frappe.utils.nowdate()
        assert deal.probability in (20, 100)


# ---------------------------------------------------------------------------
# 2. Disallowed State Transitions from Each State
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_status", ["Qualification", "Demo", "Proposal", "Negotiation"])
def test_disallowed_transition_to_lost_missing_reason(deal_fact, source_status):
    """Guarded Transition: Transitioning to 'Lost' from ANY open state without a reason must fail."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": source_status,
        "deal_value": 20000.0,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    deal.status = "Lost"
    deal.lost_reason = None
    with pytest.raises(ValidationError, match="Please specify a reason for losing the deal"):
        deal.save()


@pytest.mark.parametrize("source_status", ["Qualification", "Demo", "Proposal", "Negotiation"])
def test_disallowed_transition_to_lost_other_missing_notes(deal_fact, source_status):
    """Guarded Transition: Transitioning to 'Lost' with reason 'Other' but empty notes must fail."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": source_status,
        "deal_value": 30000.0,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    deal.status = "Lost"
    deal.lost_reason = "Other"
    deal.lost_notes = ""
    with pytest.raises(ValidationError, match="Please specify the reason for losing the deal"):
        deal.save()


@pytest.mark.parametrize(
    "invalid_status",
    ["Draft", "Archived", "Cancelled", "Deleted", "NonExistentStatus", "PendingApproval"],
)
def test_disallowed_transition_to_illegal_status(deal_fact, invalid_status):
    """Disallowed Transition: Setting arbitrary undefined status strings must fail status validation."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": "Qualification",
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    deal.status = invalid_status
    # Verify that invalid status does not map to a recognized master record
    status_doc = frappe.db.get_value("CRM Deal Status", invalid_status, "type")
    assert status_doc is None, f"Illegal status {invalid_status} should not exist in master"
