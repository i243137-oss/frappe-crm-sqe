"""
Infrastructure Smoke Tests.
Verifies the test harness, fixtures, mock database, role switching, and synthetic data factories.
"""

import pytest


def test_test_environment_initialization(clean_db):
    """Verifies that mock database initializes with required status and lost reason masters."""
    assert clean_db.exists("CRM Deal Status", "Qualification") == "Qualification"
    assert clean_db.exists("CRM Deal Status", "Won") == "Won"
    assert clean_db.exists("CRM Deal Status", "Lost") == "Lost"
    assert clean_db.exists("CRM Lead Status", "New") == "New"
    assert clean_db.exists("CRM Lead Status", "Lost") == "Lost"
    assert clean_db.exists("CRM Lost Reason", "Price too high") == "Price too high"
    assert clean_db.exists("CRM Lost Reason", "Other") == "Other"


def test_role_switching_fixtures(sales_manager, sales_user, clean_db):
    """Verifies role switching between Sales Manager and Sales User."""
    from tests.team.fixtures.mock_frappe import get_roles, session

    # Initially sales_user is active from fixture
    assert session.user == "rep@example.com"
    assert "Sales User" in get_roles()
    assert "Sales Manager" not in get_roles()


def test_synthetic_leads_dataset(synthetic_leads):
    """Verifies the pre-generated synthetic leads dataset."""
    assert len(synthetic_leads) >= 4
    for item in synthetic_leads:
        assert "id" in item
        assert "payload" in item
        assert "status" in item["payload"]
        assert "email" in item["payload"]


def test_synthetic_deals_dataset(synthetic_deals):
    """Verifies the pre-generated synthetic deals dataset."""
    assert len(synthetic_deals) >= 5
    for item in synthetic_deals:
        assert "id" in item
        assert "payload" in item
        assert "status" in item["payload"]
        assert "deal_value" in item["payload"]


def test_bva_dataset(bva_data):
    """Verifies 3-point Boundary Value Analysis data structure."""
    rule = bva_data["currency_boundary_rule"]
    assert rule["rule_id"] == "BR-01"
    points = {p["point"]: p["value"] for p in rule["boundary_points"]}
    assert points["below_boundary"] == -0.01
    assert points["at_boundary"] == 0.00
    assert points["above_boundary"] == 0.01


def test_lead_and_deal_factories(lead_fact, deal_fact):
    """Verifies that factories dynamically generate unique synthetic documents."""
    lead1 = lead_fact.build_synthetic_lead()
    lead2 = lead_fact.build_synthetic_lead()
    assert lead1["name"] != lead2["name"]
    assert lead1["email"] != lead2["email"]

    lost_lead = lead_fact.build_lost_lead(lost_reason="Price too high")
    assert lost_lead["status"] == "Lost"
    assert lost_lead["lost_reason"] == "Price too high"

    deal = deal_fact.build_synthetic_deal({"deal_value": 75000})
    assert deal["deal_value"] == 75000
    assert deal["status"] == "Qualification"
