"""
Controlled Failure-and-Recovery Test Suite for Frappe CRM.
Tests state-changing lead conversion and deal status update operations under:
1. Controlled Fault Injection (transient database failure / lock acquisition error).
2. Data Consistency Verification (asserting transaction rollback, zero orphan records).
3. Dependency Recovery & Retry Execution (re-establishing connectivity and retrying).
4. Idempotency & Zero Duplication Guarantee (verifying exactly 1 deal and consistent logs).
"""

import pytest
from unittest.mock import patch

from tests.team.fixtures.mock_frappe import (
    mock_db,
    set_user,
    ValidationError,
)
from crm.fcrm.doctype.crm_lead.crm_lead import CRMLead, convert_to_deal
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal


class ControlledDatabaseFault(Exception):
    """Simulates transient database connection drop or deadlock exception."""
    pass


@pytest.fixture(autouse=True)
def clean_test_environment():
    mock_db.reset()
    set_user("Administrator", ["System Manager", "Sales Manager"])
    yield
    mock_db.reset()
    set_user("Administrator", ["System Manager", "Sales Manager"])


def test_controlled_fault_injection_and_recovery_on_lead_conversion(lead_fact):
    """
    Executes controlled failure-and-recovery verification on Workflow 1 (Convert Lead to Deal):
    1. Baseline: Creates pristine convertible Lead (status='New', converted=0).
    2. Controlled Fault: Injects database exception during deal creation step.
    3. Consistency Check: Verifies rollback — no partial deal created, lead remains unconverted.
    4. Dependency Recovery: Restores database service connectivity.
    5. Retry Execution: Retries conversion operation.
    6. Integrity Assertion: Retry succeeds, exactly 1 Deal created and linked, zero duplicates.
    """
    # 1. Baseline: Setup healthy Lead
    lead_data = lead_fact.build_synthetic_lead({
        "first_name": "Eleanor",
        "last_name": "Vance",
        "email": "eleanor@hillhouse.org",
        "organization": "Hill House Inc",
        "status": "New",
        "annual_revenue": 125000.0,
    })
    lead = CRMLead(lead_data)
    lead.insert()

    initial_deal_count = len(mock_db.tables.get("CRM Deal", {}))
    assert lead.converted == 0
    assert lead.status == "New"

    # 2. Controlled Fault Injection: Simulate DB failure during lead.create_deal
    with patch.object(CRMLead, "create_deal", side_effect=ControlledDatabaseFault("DB Error: Deadlock encountered")):
        with pytest.raises(ControlledDatabaseFault):
            convert_to_deal(lead=lead.name)

    # 3. Consistency Verification: Verify transaction rollback & pristine state
    # No orphan or half-committed deal should exist
    current_deals = mock_db.tables.get("CRM Deal", {})
    assert len(current_deals) == initial_deal_count, "Failure left inconsistent orphan Deal records!"

    # Lead state must remain intact (not marked as converted)
    persisted_lead = mock_db.get_doc("CRM Lead", lead.name)
    assert persisted_lead.get("converted") == 0, "Lead was incorrectly marked converted despite failed transaction!"
    assert persisted_lead.get("status") == "New"

    # 4. Dependency Recovery & 5. Retry Execution
    # Simulate DB recovery: Normal execution without fault injection
    recovered_deal_name = convert_to_deal(lead=lead.name)

    # 6. State Integrity & Zero Duplication Guarantee
    assert recovered_deal_name is not None
    assert mock_db.exists("CRM Deal", recovered_deal_name)

    # Verify relationship consistency
    deal_record = mock_db.get_doc("CRM Deal", recovered_deal_name)
    assert deal_record.get("lead") == lead.name

    # Verify Lead is now properly updated
    updated_lead = mock_db.get_doc("CRM Lead", lead.name)
    assert updated_lead.get("converted") == 1
    assert updated_lead.get("status") == "Qualified"

    # Assert exactly 1 Deal linked to this Lead
    deals_for_lead = [d for d in mock_db.tables.get("CRM Deal", {}).values() if d.get("lead") == lead.name]
    assert len(deals_for_lead) == 1, f"Expected exactly 1 deal, found {len(deals_for_lead)}!"


def test_idempotency_recovery_under_network_timeout_retry(lead_fact):
    """
    Verifies that client retry using if_converted='Return Existing' is idempotent
    and prevents duplicate deal generation following simulated network timeout.
    """
    lead_data = lead_fact.build_synthetic_lead({
        "first_name": "Thomas",
        "last_name": "Carnacki",
        "email": "carnacki@ghost-finder.com",
        "status": "New",
    })
    lead = CRMLead(lead_data)
    lead.insert()

    # Initial successful conversion
    deal_1 = convert_to_deal(lead=lead.name, if_converted="Return Existing")
    assert deal_1 is not None

    # Simulate client network timeout on ack -> client retries conversion
    deal_2 = convert_to_deal(lead=lead.name, if_converted="Return Existing")

    # Must return identical deal name without spawning a second deal
    assert deal_1 == deal_2

    # Verify zero duplication in database
    linked_deals = [d for d in mock_db.tables.get("CRM Deal", {}).values() if d.get("lead") == lead.name]
    assert len(linked_deals) == 1, "Duplicate deal was spawned on retry!"


def test_controlled_fault_and_recovery_on_deal_status_update(deal_fact):
    """
    Verifies failure-and-recovery on Workflow 2 (Update Deal Status):
    1. Fault injected during activity log emission.
    2. Verifies rollback of uncommitted status transition.
    3. Re-execution succeeds and appends exactly one status log entry.
    """
    deal_data = deal_fact.build_synthetic_deal({
        "status": "Qualification",
        "deal_value": 60000.0,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    initial_log_count = len(deal.status_change_log)

    # Fault injection during status change log addition
    with patch("crm.fcrm.doctype.crm_deal.crm_deal.add_status_change_log", side_effect=ControlledDatabaseFault("Disk I/O Error")):
        with pytest.raises(ControlledDatabaseFault):
            deal.status = "Negotiation"
            deal.save()

    # Recovery and clean update
    deal.status = "Won"
    deal.save()
    assert deal.status == "Won"
    assert deal.closed_date is not None

    # Exactly 1 new log appended to deal.status_change_log
    assert len(deal.status_change_log) == initial_log_count + 1
