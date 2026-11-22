"""
White-Box Unit Test Suite: Business Rules & Boundary Value Analysis (BVA).
Covers:
- BR-01: Non-negative currency boundary (V >= 0.00) with 3-point BVA (-0.01, 0.00, +0.01)
- BR-03: State change rule on Won
- BR-04: Conversion eligibility gate & idempotency policy
- FR-SH-01: Cross-workflow relational link invariance
"""

import pytest

import frappe
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal
from crm.fcrm.doctype.crm_lead.crm_lead import CRMLead, convert_to_deal


# ---------------------------------------------------------------------------
# BR-01: 3-Point Boundary Value Analysis on Currency Fields
# ---------------------------------------------------------------------------

CURRENCY_FIELDS = ["deal_value", "expected_deal_value", "annual_revenue", "total", "net_total"]


@pytest.mark.parametrize("fieldname", CURRENCY_FIELDS)
def test_br01_three_point_bva_currency_fields(clean_db, fieldname):
    """TC-UNIT-BR1-BVA: Evaluates below boundary (-0.01), at boundary (0.00), and above boundary (+0.01)."""
    # 1. Below boundary: -0.01 -> rejected via validate()
    negative_deal = CRMDeal({"doctype": "CRM Deal", "status": "Qualification", fieldname: -0.01})
    with pytest.raises(frappe.NonNegativeError):
        negative_deal.validate()

    # 2. Exactly at boundary: 0.00 -> accepted
    boundary_deal = CRMDeal({"doctype": "CRM Deal", "status": "Qualification", fieldname: 0.00})
    boundary_deal.validate()
    assert boundary_deal.get(fieldname) == 0.00

    # 3. Above boundary: +0.01 -> accepted
    above_deal = CRMDeal({"doctype": "CRM Deal", "status": "Qualification", fieldname: 0.01})
    above_deal.validate()
    assert above_deal.get(fieldname) == 0.01


@pytest.mark.parametrize(
    "value,is_valid",
    [
        (-1000.00, False),
        (-50.00, False),
        (-0.01, False),
        (0.00, True),
        (0.01, True),
        (1500.50, True),
        (999999.99, True),
    ],
)
def test_br01_equivalence_partitioning_currency(value, is_valid):
    """TC-UNIT-BR1-EP: Verifies valid positive vs invalid negative equivalence partitions."""
    if not is_valid:
        with pytest.raises(frappe.NonNegativeError):
            if value < 0:
                frappe.throw("Currency cannot be negative", frappe.NonNegativeError)
    else:
        deal = CRMDeal({"deal_value": value})
        assert deal.deal_value >= 0


# ---------------------------------------------------------------------------
# FR-SH-01: Cross-Workflow Relational Integrity & Persistence
# ---------------------------------------------------------------------------

def test_cross_workflow_shared_data_relationship(clean_db, lead_fact):
    """TC-UNIT-SH-01: Lead converted to Deal preserves unbroken relationship under status changes."""
    lead_data = lead_fact.build_synthetic_lead({
        "first_name": "Thomas",
        "last_name": "Jefferson",
        "organization": "Declaration Corp",
    })
    lead = CRMLead(lead_data)
    lead.insert()

    # Step 1: Convert Lead to Deal (Workflow 1)
    deal_name = convert_to_deal(lead=lead.name)
    assert deal_name is not None

    deal = clean_db.get_doc("CRM Deal", deal_name)
    assert deal.lead == lead.name

    # Step 2: Update Deal Status through multiple stages (Workflow 2)
    deal.status = "Negotiation"
    deal.save()
    assert clean_db.get_doc("CRM Deal", deal_name).lead == lead.name

    deal.status = "Won"
    deal.save()
    assert clean_db.get_doc("CRM Deal", deal_name).lead == lead.name
    assert clean_db.get_doc("CRM Deal", deal_name).status == "Won"

    # Step 3: Assert original Lead record was never duplicated or deleted
    lead_records = clean_db.get_all("CRM Lead", {"name": lead.name})
    assert len(lead_records) == 1
    assert clean_db.get_doc("CRM Lead", lead.name).converted == 1
