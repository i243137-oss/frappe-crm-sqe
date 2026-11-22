"""
White-Box Unit Test Suite: Status Change Audit Logging & Duration Tracking.
Targets: crm/crm/fcrm/doctype/crm_status_change_log/crm_status_change_log.py
Covers:
- FR-DS-03: Status Change Audit Logging, from/to transition recording, duration calculation, and session user logging.
"""

from datetime import datetime, timedelta
import pytest

import frappe
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal
from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import (
    add_status_change_log,
    get_duration,
)
from tests.team.fixtures.mock_frappe import set_user


def test_get_duration_calculation():
    """Verifies duration calculation between datetime objects and ISO strings."""
    t1 = datetime(2026, 11, 22, 10, 0, 0)
    t2 = datetime(2026, 11, 22, 10, 5, 30)

    # 5 minutes and 30 seconds = 330 seconds
    assert get_duration(t1, t2) == 330.0

    # String format parsing
    str_t1 = "2026-11-22 10:00:00"
    str_t2 = "2026-11-22 10:01:00"
    assert get_duration(str_t1, str_t2) == 60.0


def test_status_change_log_created_on_new_deal(clean_db):
    """Verifies initial active status log created when new document is inserted."""
    set_user("rep1@example.com", ["Sales User"])

    deal = CRMDeal({"status": "Qualification"})
    deal.status_change_log = []
    add_status_change_log(deal)

    assert len(deal.status_change_log) == 1
    initial_log = deal.status_change_log[0]
    assert initial_log.get("from") == "Qualification"
    assert initial_log.get("to") == ""
    assert initial_log.get("log_owner") == "rep1@example.com"
    assert initial_log.get("from_date") is not None


def test_status_change_log_updated_on_status_transition(clean_db):
    """Verifies existing log entry is completed with to_date and duration, and new log appended."""
    set_user("rep1@example.com", ["Sales User"])

    deal = CRMDeal({"status": "Qualification"})
    deal.insert()

    # deal.insert() already added initial status log
    assert len(deal.status_change_log) == 1
    initial_log = deal.status_change_log[0]
    assert initial_log.get("from") == "Qualification"
    assert initial_log.get("to") == ""

    # Advance time artificially on initial log
    initial_log["from_date"] = datetime.now() - timedelta(minutes=15)

    # User changes status to Negotiation
    set_user("rep2@example.com", ["Sales User"])
    deal.status = "Negotiation"
    deal.save()

    # Now there should be exactly 2 logs: the completed first log and active second log
    assert len(deal.status_change_log) == 2

    completed_log = deal.status_change_log[0]
    assert completed_log.get("to") == "Negotiation"
    assert completed_log.get("to_date") is not None
    assert completed_log.get("duration") >= 890  # ~900s for 15 mins
    assert completed_log.get("log_owner") == "rep2@example.com"

    active_log = deal.status_change_log[1]
    assert active_log.get("from") == "Negotiation"
    assert active_log.get("to") == ""
    assert active_log.get("log_owner") == "rep2@example.com"
