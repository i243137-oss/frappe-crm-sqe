"""
Test suite validating data produced by OpenAPIDataGenerator against live/simulated endpoints.
Verifies compliance with OpenAPI spec constraints, 3-point BVA, and Equivalence Partitions.
"""

import json
import pytest
from tests.team.api.api_client import FrappeAPIClient
from tests.team.fixtures.lead_factory import build_synthetic_lead
from tests.team.fixtures.deal_factory import build_synthetic_deal
from tests.team.generator.data_generator import OpenAPIDataGenerator


@pytest.fixture
def client():
    return FrappeAPIClient()


@pytest.fixture(scope="module")
def generated_data():
    generator = OpenAPIDataGenerator()
    return generator.generate_all()


def test_generator_metadata_and_integrity(generated_data):
    """Verify that the generator produces structured datasets containing all required testing categories."""
    assert "metadata" in generated_data
    assert "bva_currency" in generated_data
    assert "bva_probability" in generated_data
    assert "ep_currency" in generated_data
    assert "lead_conversion_cases" in generated_data
    assert "deal_status_cases" in generated_data
    assert len(generated_data["bva_currency"]) == 3
    assert len(generated_data["bva_probability"]) == 6


def test_execute_generated_lead_conversion_cases(clean_db, client, generated_data):
    """Executes the dynamically generated lead conversion cases against the API."""
    cases = generated_data["lead_conversion_cases"]

    for case in cases:
        payload = case["payload"].copy()

        # If lead is specified, ensure it exists in DB via REST API
        if "lead" in payload:
            lead_data = build_synthetic_lead({"name": payload["lead"], "status": "New"})
            client.post("/api/resource/CRM Lead", lead_data)

        res = client.post(
            "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal",
            payload
        )

        assert res.status_code == case["expected_status"], (
            f"Case {case['case_id']} failed: Expected {case['expected_status']} but got {res.status_code} ({res.json()})"
        )


def test_execute_generated_deal_status_cases(clean_db, client, generated_data):
    """Executes the dynamically generated deal status cases against the API."""
    cases = generated_data["deal_status_cases"]

    for case in cases:
        deal_data = build_synthetic_deal({"status": "Opportunity", "deal_value": 50000.0})
        res_create = client.post("/api/resource/CRM Deal", deal_data)
        deal_name = res_create.json()["data"]["name"]

        payload = case["payload"]
        res = client.put(f"/api/resource/CRM Deal/{deal_name}", payload)

        assert res.status_code == case["expected_status"], (
            f"Case {case['case_id']} failed: Expected {case['expected_status']} but got {res.status_code} ({res.json()})"
        )


def test_execute_generated_bva_currency(clean_db, client, generated_data):
    """Executes the generated 3-point boundary value analysis cases on deal value."""
    bva_cases = generated_data["bva_currency"]

    for case in bva_cases:
        deal_data = build_synthetic_deal({"status": "Opportunity", "deal_value": 1000.0})
        res_create = client.post("/api/resource/CRM Deal", deal_data)
        deal_name = res_create.json()["data"]["name"]

        res = client.put(f"/api/resource/CRM Deal/{deal_name}", {"deal_value": case["value"]})

        if case["expected_valid"]:
            assert res.status_code == 200, f"Expected valid boundary for {case['value']}"
        else:
            assert res.status_code == 400, f"Expected invalid boundary rejection for {case['value']}"
