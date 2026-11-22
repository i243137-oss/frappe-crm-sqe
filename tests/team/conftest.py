"""
Master Pytest Configuration and Shared Fixtures for Team Test Suite.
Initializes the mock Frappe environment, manages in-memory database lifecycle,
and provides authenticated role contexts and synthetic test data fixtures.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure project root and crm directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRM_PATH = PROJECT_ROOT / "crm"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CRM_PATH) not in sys.path:
    sys.path.insert(0, str(CRM_PATH))

# Initialize mock frappe environment before importing any CRM modules
from tests.team.fixtures.mock_frappe import (
    mock_db,
    session,
    set_user,
    setup_mock_frappe,
)

frappe = setup_mock_frappe()

from tests.team.fixtures import deal_factory, lead_factory


@pytest.fixture(autouse=True)
def clean_db():
    """Resets mock database tables and single values to pristine state before each test."""
    mock_db.reset()
    set_user("Administrator", ["System Manager", "Sales Manager"])
    yield mock_db


@pytest.fixture
def sales_manager():
    """Simulates an active authenticated session for a Sales Manager."""
    set_user("manager@example.com", ["Sales Manager"])
    return "manager@example.com"


@pytest.fixture
def sales_user():
    """Simulates an active authenticated session for a standard Sales User."""
    set_user("rep@example.com", ["Sales User"])
    return "rep@example.com"


@pytest.fixture
def synthetic_leads():
    """Loads pre-generated synthetic leads dataset."""
    path = PROJECT_ROOT / "tests" / "team" / "data" / "synthetic_leads.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def synthetic_deals():
    """Loads pre-generated synthetic deals dataset."""
    path = PROJECT_ROOT / "tests" / "team" / "data" / "synthetic_deals.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def bva_data():
    """Loads 3-point boundary value analysis dataset."""
    path = PROJECT_ROOT / "tests" / "team" / "data" / "bva_test_data.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def lead_fact():
    return lead_factory


@pytest.fixture
def deal_fact():
    return deal_factory
