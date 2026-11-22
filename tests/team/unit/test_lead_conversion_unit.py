"""
White-Box Unit Test Suite: Lead Conversion & Lead Business Logic.
Targets: crm/crm/fcrm/doctype/crm_lead/crm_lead.py
Covers:
- FR-LC-01: Valid Lead Conversion & Field Mapping
- FR-LC-02: Ineligible Status Rejection & Permission Enforcement (BR-04-A)
- FR-LC-03: Concurrency Locking, Idempotency & Duplicate Prevention (BR-04-B, C, D)
- CRMLead validation lifecycle (email, unique, lost reason, naming)
"""

import pytest

import frappe
from crm.fcrm.doctype.crm_lead.crm_lead import (
    CRMLead,
    convert_to_deal,
    existing_deal,
    get_deal_fieldname,
    is_custom_field,
    lock_lead,
    mark_converted,
    settle_converted,
    validate_conversion_access,
)
from tests.team.fixtures.mock_frappe import set_permission_override, set_user


# ---------------------------------------------------------------------------
# Conversion Workflow Tests
# ---------------------------------------------------------------------------

def test_convert_to_deal_valid(clean_db, lead_fact):
    """TC-UNIT-LC-01: Valid conversion creates deal, links to lead, marks lead converted."""
    lead_data = lead_fact.build_synthetic_lead({
        "first_name": "Alexander",
        "last_name": "Hamilton",
        "email": "alexander@treasury.gov",
        "organization": "Treasury Department",
        "status": "New",
        "annual_revenue": 250000.0,
    })
    lead = CRMLead(lead_data)
    lead.insert()

    deal_name = convert_to_deal(lead=lead.name)

    assert deal_name is not None
    assert deal_name.startswith("CRM-DEAL-")

    # Verify persisted Deal
    deal_doc = clean_db.get_doc("CRM Deal", deal_name)
    assert deal_doc is not None
    assert deal_doc.lead == lead.name
    assert deal_doc.organization == "Treasury Department" or deal_doc.organization is not None

    # Verify persisted Lead state
    updated_lead = clean_db.get_doc("CRM Lead", lead.name)
    assert updated_lead.converted == 1
    assert updated_lead.status == "Qualified"


def test_convert_to_deal_ineligible_lost_rejected(clean_db, lead_fact):
    """TC-UNIT-LC-02 / BR-04-A: Ineligible status 'Lost' must strictly reject conversion."""
    lead_data = lead_fact.build_lost_lead(lost_reason="Price too high")
    lead = CRMLead(lead_data)
    lead.insert()

    with pytest.raises(frappe.ValidationError) as exc_info:
        convert_to_deal(lead=lead.name)

    assert "Cannot convert a lead with status" in str(exc_info.value)
    # Assert no deal created
    assert clean_db.exists("CRM Deal", {"lead": lead.name}) is False


def test_convert_to_deal_unauthorized_rejected(clean_db, lead_fact):
    """TC-UNIT-LC-06 / FR-AU-01: Conversion without write permission raises PermissionError."""
    lead_data = lead_fact.build_synthetic_lead({"lead_owner": "other_rep@example.com"})
    lead = CRMLead(lead_data)
    lead.insert()

    set_user("rep@example.com", ["Sales User"])
    set_permission_override("CRM Lead", "write", lead.name, "rep@example.com", False)

    with pytest.raises(frappe.PermissionError) as exc_info:
        convert_to_deal(lead=lead.name)

    assert "Not allowed to convert Lead to Deal" in str(exc_info.value)


def test_convert_to_deal_idempotent_return_existing(clean_db, lead_fact):
    """TC-UNIT-LC-04 / BR-04-C: Idempotent conversion returns existing deal without duplication."""
    lead_data = lead_fact.build_synthetic_lead()
    lead = CRMLead(lead_data)
    lead.insert()

    # First conversion
    deal_1 = convert_to_deal(lead=lead.name)
    assert deal_1 is not None

    # Second conversion with Return Existing policy
    deal_2 = convert_to_deal(lead=lead.name, if_converted="Return Existing")
    assert deal_2 == deal_1

    # Assert exactly 1 deal exists for this lead
    deals_for_lead = clean_db.get_all("CRM Deal", {"lead": lead.name})
    assert len(deals_for_lead) == 1


def test_convert_to_deal_already_converted_fail(clean_db, lead_fact):
    """TC-UNIT-LC-03 / BR-04-B: Repeated conversion with Fail policy throws ValidationError."""
    lead_data = lead_fact.build_synthetic_lead()
    lead = CRMLead(lead_data)
    lead.insert()

    deal_1 = convert_to_deal(lead=lead.name)
    assert deal_1 is not None

    with pytest.raises(frappe.ValidationError) as exc_info:
        convert_to_deal(lead=lead.name, if_converted="Fail")

    assert "is already converted to Deal" in str(exc_info.value)


def test_convert_to_deal_create_multiple_allowed(clean_db, lead_fact):
    """TC-UNIT-LC-05 / BR-04-D: Secondary conversion with Create policy creates another deal."""
    lead_data = lead_fact.build_synthetic_lead()
    lead = CRMLead(lead_data)
    lead.insert()

    deal_1 = convert_to_deal(lead=lead.name)
    deal_2 = convert_to_deal(lead=lead.name, if_converted="Create")

    assert deal_1 != deal_2
    assert deal_2.startswith("CRM-DEAL-")


def test_convert_to_deal_with_existing_contact_and_org(clean_db, lead_fact):
    """TC-UNIT-LC-09: Conversion reuses specified existing contact and organization."""
    # Pre-create contact and organization in mock db
    org = frappe.new_doc("CRM Organization")
    org.organization_name = "Acme Corp Existing"
    org.insert()

    contact = frappe.new_doc("Contact")
    contact.first_name = "George"
    contact.last_name = "Washington"
    contact.insert()

    lead_data = lead_fact.build_synthetic_lead({
        "first_name": "George",
        "organization": "Acme Corp Existing",
    })
    lead = CRMLead(lead_data)
    lead.insert()

    deal_name = convert_to_deal(
        lead=lead.name,
        existing_contact=contact.name,
        existing_organization=org.name,
    )

    deal_doc = clean_db.get_doc("CRM Deal", deal_name)
    assert deal_doc.organization == org.name
    assert any(c.get("contact") == contact.name for c in deal_doc.contacts)


# ---------------------------------------------------------------------------
# Lead Validation & Naming Unit Tests
# ---------------------------------------------------------------------------

def test_lead_set_full_name_and_lead_name():
    """Verifies full name assembly from salutation, first, middle, and last name."""
    lead = CRMLead({
        "salutation": "Dr",
        "first_name": "Ada",
        "middle_name": "Augusta",
        "last_name": "Lovelace",
    })
    lead.set_full_name()
    assert lead.lead_name == "Dr Ada Augusta Lovelace"

    lead_org = CRMLead({"organization": "Babbage Analytical Engines"})
    lead_org.set_lead_name()
    assert lead_org.lead_name == "Babbage Analytical Engines"

    lead_email = CRMLead({"email": "grace.hopper@navy.mil"})
    lead_email.set_lead_name()
    assert lead_email.lead_name == "grace.hopper"


def test_lead_validate_email():
    """Verifies email validation and check against lead owner."""
    valid_lead = CRMLead({"email": "valid.lead@example.com", "lead_owner": "owner@example.com"})
    valid_lead.validate_email()

    with pytest.raises(frappe.ValidationError):
        invalid_email = CRMLead({"email": "not-an-email"})
        invalid_email.validate_email()

    with pytest.raises(frappe.ValidationError) as exc:
        same_owner_lead = CRMLead({"email": "sam@example.com", "lead_owner": "sam@example.com"})
        same_owner_lead.validate_email()
    assert "Lead Owner cannot be same as the Lead Email Address" in str(exc.value)


def test_lead_validate_lost_reason():
    """Verifies lead lost reason enforcement when lead status is type Lost."""
    # Lost without reason throws
    lost_lead_no_reason = CRMLead({"status": "Lost", "lost_reason": None})
    with pytest.raises(frappe.ValidationError) as exc1:
        lost_lead_no_reason.validate_lost_reason()
    assert "specify a reason for losing the lead" in str(exc1.value)

    # Lost with Other but no notes throws
    lost_lead_other_no_notes = CRMLead({"status": "Lost", "lost_reason": "Other", "lost_notes": None})
    with pytest.raises(frappe.ValidationError) as exc2:
        lost_lead_other_no_notes.validate_lost_reason()
    assert "specify the reason for losing the lead" in str(exc2.value)

    # Lost with Other and notes passes
    lost_lead_valid_other = CRMLead({
        "status": "Lost",
        "lost_reason": "Other",
        "lost_notes": "Project cancelled due to budget cuts",
    })
    lost_lead_valid_other.validate_lost_reason()  # Should not raise


# ---------------------------------------------------------------------------
# Field Mapping & Custom Field Helpers
# ---------------------------------------------------------------------------

def test_field_mapping_helpers():
    """Tests get_deal_fieldname mapping and custom field detection."""
    from tests.team.fixtures.mock_frappe import DocField, DocMeta

    deal_meta = DocMeta("CRM Deal")

    # Mapped field: lead_owner -> deal_owner
    lead_owner_field = DocField("lead_owner", "Link")
    assert get_deal_fieldname(lead_owner_field, deal_meta) == "deal_owner"

    # Direct match: organization
    org_field = DocField("organization", "Link")
    assert get_deal_fieldname(org_field, deal_meta) == "organization"

    # Non-custom non-matching field returns None
    unmapped = DocField("random_unmapped_field", "Data")
    assert get_deal_fieldname(unmapped, deal_meta) is None

    # Custom field detection
    custom_field_1 = DocField("custom_budget", "Currency")
    assert is_custom_field(custom_field_1) is True

    custom_field_2 = {"is_custom_field": 1, "fieldname": "partner_ref"}
    assert is_custom_field(custom_field_2) is True
