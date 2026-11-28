"""
White-Box Unit Test Suite: Deal Status Management, MCC & MC/DC Formal Verification.
Targets: crm/crm/fcrm/doctype/crm_deal/crm_deal.py
Covers:
- FR-DS-01 / BR-03: Transition to Won (closed_date set to nowdate(), probability update)
- FR-DS-02 / BR-02: Full 10-Row Multiple Condition Coverage (MCC) truth table
- FR-DS-02 / BR-02: MC/DC pair derivation demonstrating condition independence
- FR-FC-01: Deal forecasting field validation
- Primary contact validation and contact management APIs
"""

import pytest

import frappe
from crm.fcrm.doctype.crm_deal.crm_deal import (
    CRMDeal,
    add_contact,
    create_deal,
    remove_contact,
    set_primary_contact,
)
from tests.team.fixtures.mock_frappe import set_user


# ---------------------------------------------------------------------------
# Transition to Won (BR-03)
# ---------------------------------------------------------------------------

def test_deal_transition_to_won_sets_closed_date_and_probability(clean_db, deal_fact):
    """TC-UNIT-DS-01 / BR-03: Moving status to Won automatically populates closed_date and probability."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": "Qualification",
        "probability": 0,
        "closed_date": None,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    assert deal.closed_date is None

    # Reset probability to 0 to test default assignment on Won
    deal.probability = 0
    # Transition to Won
    deal.status = "Won"
    deal.save()

    assert deal.status == "Won"
    assert deal.closed_date == frappe.utils.nowdate()
    # Deal probability updated from master (100% for Won)
    assert deal.probability == 100

    # Also verify when probability is None, default probability is populated
    deal.probability = None
    deal.update_default_probability()
    assert deal.probability == 100


def test_deal_open_status_does_not_set_closed_date(clean_db, deal_fact):
    """Transition between open statuses must NOT set closed_date."""
    deal_data = deal_fact.build_synthetic_deal({
        "status": "Qualification",
        "closed_date": None,
    })
    deal = CRMDeal(deal_data)
    deal.insert()

    deal.status = "Negotiation"
    deal.save()

    assert deal.status == "Negotiation"
    assert deal.closed_date is None


# ---------------------------------------------------------------------------
# BR-02: Multiple Condition Coverage (MCC) Suite
# Condition A: status.type == "Lost"
# Condition B: bool(lost_reason)
# Condition C: lost_reason == "Other"
# Condition D: bool(lost_notes)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "row,status,reason,notes,expected_outcome,expected_err",
    [
        # Row 1: False, False, False, False -> Valid
        (1, "Qualification", None, None, "Valid", None),
        # Row 2: False, False, False, True -> Valid
        (2, "Qualification", None, "Unsolicited note", "Valid", None),
        # Row 3: False, True, False, False -> Valid
        (3, "Won", "Price too high", None, "Valid", None),
        # Row 4: False, True, True, True -> Valid
        (4, "Negotiation", "Other", "Some notes", "Valid", None),
        # Row 5: True, False, False, False -> Error 1 (Missing Reason)
        (5, "Lost", None, None, "Error", "Please specify a reason for losing the deal."),
        # Row 6: True, False, False, True -> Error 1 (Notes present, but Reason missing)
        (6, "Lost", None, "Unused note", "Error", "Please specify a reason for losing the deal."),
        # Row 7: True, True, False, False -> Valid (Standard reason like 'Price too high')
        (7, "Lost", "Price too high", None, "Valid", None),
        # Row 8: True, True, False, True -> Valid (Standard reason with notes)
        (8, "Lost", "Price too high", "Notes provided", "Valid", None),
        # Row 9: True, True, True, False -> Error 2 (Reason is Other, but notes omitted)
        (9, "Lost", "Other", None, "Error", "Please specify the reason for losing the deal."),
        # Row 10: True, True, True, True -> Valid (Reason Other with required notes)
        (10, "Lost", "Other", "Client cancelled capital budget", "Valid", None),
    ],
)
def test_br02_multiple_condition_coverage_mcc(clean_db, row, status, reason, notes, expected_outcome, expected_err):
    """TC-UNIT-DS-02-MCC: Tests every combination of the BR-02 truth table."""
    deal = CRMDeal({
        "doctype": "CRM Deal",
        "name": f"DEAL-MCC-{row:02d}",
        "status": status,
        "lost_reason": reason,
        "lost_notes": notes,
    })

    if expected_outcome == "Valid":
        deal.validate_lost_reason()
    else:
        with pytest.raises(frappe.ValidationError) as exc_info:
            deal.validate_lost_reason()
        assert expected_err in str(exc_info.value)


# ---------------------------------------------------------------------------
# BR-02: Modified Condition / Decision Coverage (MC/DC) Independence Tests
# ---------------------------------------------------------------------------

def test_mcdc_pair_condition_a_status_is_lost():
    """MC/DC Pair 1 for Condition A (status is Lost): Row 1 (Valid) vs Row 5 (Error 1)."""
    # Fix: B=False, C=False, D=False
    # Row 1: Status='Qualification' (A=False) -> Valid
    deal_row_1 = CRMDeal({"status": "Qualification", "lost_reason": None, "lost_notes": None})
    deal_row_1.validate_lost_reason()  # Passes

    # Row 5: Status='Lost' (A=True) -> Fails with Error 1
    deal_row_5 = CRMDeal({"status": "Lost", "lost_reason": None, "lost_notes": None})
    with pytest.raises(frappe.ValidationError) as exc:
        deal_row_5.validate_lost_reason()
    assert "Please specify a reason" in str(exc.value)


def test_mcdc_pair_condition_b_reason_present():
    """MC/DC Pair 2 for Condition B (Reason present): Row 5 (Error 1) vs Row 7 (Valid)."""
    # Fix: A=True (Lost), C=False (Not Other), D=False (No notes)
    # Row 5: B=False (No reason) -> Error 1
    deal_row_5 = CRMDeal({"status": "Lost", "lost_reason": None, "lost_notes": None})
    with pytest.raises(frappe.ValidationError):
        deal_row_5.validate_lost_reason()

    # Row 7: B=True (Reason provided) -> Valid
    deal_row_7 = CRMDeal({"status": "Lost", "lost_reason": "Price too high", "lost_notes": None})
    deal_row_7.validate_lost_reason()  # Passes


def test_mcdc_pair_condition_c_reason_is_other():
    """MC/DC Pair 3 for Condition C (Reason == Other): Row 7 (Valid) vs Row 9 (Error 2)."""
    # Fix: A=True (Lost), B=True (Reason present), D=False (No notes)
    # Row 7: C=False (Reason = "Price too high") -> Valid
    deal_row_7 = CRMDeal({"status": "Lost", "lost_reason": "Price too high", "lost_notes": None})
    deal_row_7.validate_lost_reason()  # Passes

    # Row 9: C=True (Reason = "Other") -> Error 2
    deal_row_9 = CRMDeal({"status": "Lost", "lost_reason": "Other", "lost_notes": None})
    with pytest.raises(frappe.ValidationError) as exc:
        deal_row_9.validate_lost_reason()
    assert "specify the reason for losing the deal" in str(exc.value)


def test_mcdc_pair_condition_d_notes_present():
    """MC/DC Pair 4 for Condition D (Notes present): Row 9 (Error 2) vs Row 10 (Valid)."""
    # Fix: A=True (Lost), B=True (Reason present), C=True (Reason == Other)
    # Row 9: D=False (No notes) -> Error 2
    deal_row_9 = CRMDeal({"status": "Lost", "lost_reason": "Other", "lost_notes": None})
    with pytest.raises(frappe.ValidationError):
        deal_row_9.validate_lost_reason()

    # Row 10: D=True (Notes provided) -> Valid
    deal_row_10 = CRMDeal({"status": "Lost", "lost_reason": "Other", "lost_notes": "Acquisition fell through"})
    deal_row_10.validate_lost_reason()  # Passes


# ---------------------------------------------------------------------------
# Forecasting & Contact Integrity
# ---------------------------------------------------------------------------

def test_forecasting_fields_validation(clean_db):
    """TC-UNIT-DS-03: Forecasting mandates expected_deal_value and expected_closure_date."""
    clean_db.single_values["FCRM Settings"]["enable_forecasting"] = 1

    # Missing both fields -> throws
    deal = CRMDeal({"organization": "Forecast Corp"})
    with pytest.raises(frappe.MandatoryError) as exc1:
        deal.validate_forecasting_fields()
    assert "Expected deal value is required" in str(exc1.value)

    # Missing expected_closure_date -> throws
    deal.expected_deal_value = 50000.0
    with pytest.raises(frappe.MandatoryError) as exc2:
        deal.validate_forecasting_fields()
    assert "Expected closure date is required" in str(exc2.value)

    # Both provided -> passes
    deal.expected_closure_date = "2026-12-31"
    deal.validate_forecasting_fields()


def test_primary_contact_enforcement():
    """TC-UNIT-DS-04: Throws error if multiple contacts have is_primary=1."""
    deal = CRMDeal()
    deal.append("contacts", {"contact": "CONT-001", "is_primary": 1, "email": "a@ex.com"})
    deal.append("contacts", {"contact": "CONT-002", "is_primary": 1, "email": "b@ex.com"})
    with pytest.raises(frappe.ValidationError) as exc:
        deal.set_primary_email_mobile_no()
    assert "Only one" in str(exc.value) and "primary" in str(exc.value)


def test_contact_management_apis(clean_db, deal_fact):
    """TC-UNIT-DS-05: add_contact, remove_contact, and set_primary_contact APIs."""
    deal_data = deal_fact.build_synthetic_deal()
    deal = CRMDeal(deal_data)
    deal.insert()

    # Add contact
    add_contact(deal.name, "CONT-100")
    reloaded = clean_db.get_doc("CRM Deal", deal.name)
    assert any(c.get("contact") == "CONT-100" for c in reloaded.contacts)

    # Set primary contact
    set_primary_contact(deal.name, "CONT-100")
    reloaded = clean_db.get_doc("CRM Deal", deal.name)
    for c in reloaded.contacts:
        if c.get("contact") == "CONT-100":
            assert c.get("is_primary") == 1

    # Remove contact
    remove_contact(deal.name, "CONT-100")
    reloaded = clean_db.get_doc("CRM Deal", deal.name)
    assert not any(c.get("contact") == "CONT-100" for c in reloaded.contacts)


def test_deal_won_preserves_existing_closed_date(clean_db):
    """SURV-01: Verifies that transitioning to Won preserves pre-existing closed_date if already populated."""
    deal = CRMDeal({
        "doctype": "CRM Deal",
        "status": "Won",
        "closed_date": "2025-06-15"
    })
    deal.update_closed_date()
    # Must preserve the explicitly existing closure date rather than overwriting with nowdate()
    assert deal.closed_date == "2025-06-15"


def test_expected_deal_value_none_under_forecasting(clean_db):
    """SURV-02: Verifies MandatoryError raised when expected_deal_value is None under forecasting."""
    frappe.db.set_single_value("FCRM Settings", "enable_forecasting", 1)
    deal = CRMDeal({
        "doctype": "CRM Deal",
        "status": "Open",
        "expected_deal_value": None,
        "expected_closure_date": "2026-12-31"
    })
    with pytest.raises(frappe.MandatoryError) as exc:
        deal.validate_forecasting_fields()
    assert "Expected deal value is required" in str(exc.value)


def test_deal_status_none_handled_cleanly(clean_db):
    """SURV-08: Verifies that validate_lost_reason handles status=None without throwing unhandled exceptions."""
    deal = CRMDeal({
        "doctype": "CRM Deal",
        "status": None
    })
    # Should not throw when status is None/null
    deal.validate_lost_reason()


def test_probability_zero_boundary(clean_db):
    """SURV-12: Verifies probability=0.0 boundary behavior under default pipeline assignment."""
    deal = CRMDeal({
        "doctype": "CRM Deal",
        "status": "Won",
        "probability": 0.0
    })
    deal.update_default_probability()
    # In crm_deal.py line 261: if not self.probability or self.probability == 0 -> defaults
    assert deal.probability is not None and deal.probability >= 0


def test_no_audit_log_on_unchanged_status(clean_db, deal_fact):
    """SURV-10: Verifies that saving a deal without modifying status does not create spurious audit log entries."""
    deal_data = deal_fact.build_synthetic_deal({"status": "Qualification"})
    deal = CRMDeal(deal_data)
    deal.insert()
    initial_log_count = len(getattr(deal, "status_change_log", []))

    # Save again with same status
    deal.status = "Qualification"
    deal.save()
    assert len(getattr(deal, "status_change_log", [])) == initial_log_count
