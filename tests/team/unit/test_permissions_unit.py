"""
White-Box Unit Test Suite: Role-Based Authorization & Permission Scoping.
Targets: crm/crm/permissions/org_hierarchy.py
Covers:
- FR-AU-01: Sales Manager vs. Sales User Query Scoping & Access Control
"""

import pytest

import frappe
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal
from crm.fcrm.doctype.crm_lead.crm_lead import CRMLead
from crm.permissions.org_hierarchy import (
    _has_permission,
    has_deal_permission,
    has_lead_permission,
    permission_query_conditions,
)
from tests.team.fixtures.mock_frappe import set_user


def test_permission_query_conditions_administrator():
    """Administrator receives empty string (unrestricted global access)."""
    assert permission_query_conditions("Administrator", "CRM Lead") == ""
    assert permission_query_conditions("Administrator", "CRM Deal") == ""


def test_permission_query_conditions_sales_manager():
    """Sales Manager outside hierarchy receives empty string (unrestricted global access)."""
    set_user("sales_manager@example.com", ["Sales Manager"])
    cond_lead = permission_query_conditions("sales_manager@example.com", "CRM Lead")
    cond_deal = permission_query_conditions("sales_manager@example.com", "CRM Deal")

    assert cond_lead == ""
    assert cond_deal == ""


def test_permission_query_conditions_sales_user():
    """Sales User receives query condition scoping to own records or assigned ToDos."""
    set_user("rep_user@example.com", ["Sales User"])
    cond = permission_query_conditions("rep_user@example.com", "CRM Lead")

    # In mock QB, cond is a compound expression
    assert cond is not None
    assert cond != ""


def test_has_lead_and_deal_permission():
    """Verifies single document permission checks for Manager vs User."""
    set_user("manager@example.com", ["Sales Manager"])
    lead = CRMLead({"name": "LEAD-001", "lead_owner": "other@example.com"})
    deal = CRMDeal({"name": "DEAL-001", "deal_owner": "other@example.com"})

    # Sales Manager can access any lead and deal
    assert has_lead_permission(lead, "read", "manager@example.com") is True
    assert has_deal_permission(deal, "write", "manager@example.com") is True

    # Create permission is universally granted for authorized CRM roles
    assert has_lead_permission(lead, "create", "rep@example.com") is True
