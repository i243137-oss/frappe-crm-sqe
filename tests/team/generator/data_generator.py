"""
Automated OpenAPI Test Data Generator for Frappe CRM SQE Project.
Reads the OpenAPI 3.0 specification (`docs/openapi_crm.yaml`) or parses JSON schemas,
and systematically generates:
  1. Boundary Value Analysis (3-Point BVA: min-epsilon, min, min+epsilon)
  2. Equivalence Partitioning (EP: Valid/Invalid partitions)
  3. Positive, Negative, and Edge Case synthetic payloads
Outputs structured test fixtures in `tests/team/data/generated_api_payloads.json`.
"""

import json
import os
import re
from typing import Any, Dict, List, Tuple


class OpenAPIDataGenerator:
    """Generates synthetic test datasets directly derived from OpenAPI schemas."""

    def __init__(self, spec_path: str = "docs/openapi_crm.yaml"):
        self.spec_path = spec_path
        self.spec = self._load_spec()

    def _load_spec(self) -> Dict[str, Any]:
        """Loads OpenAPI YAML spec file."""
        if not os.path.exists(self.spec_path):
            raise FileNotFoundError(f"OpenAPI specification not found at {self.spec_path}")

        # Basic parser for YAML if pyyaml not installed or standard parsing
        try:
            import yaml
            with open(self.spec_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            # Fallback lightweight parser if yaml is not available
            return self._fallback_yaml_parse()

    def _fallback_yaml_parse(self) -> Dict[str, Any]:
        """Lightweight schema structure for core schemas if pyyaml is missing."""
        return {
            "components": {
                "schemas": {
                    "ConvertLeadRequest": {
                        "properties": {
                            "lead": {"type": "string"},
                            "deal_name": {"type": "string"},
                            "deal_value": {"type": "number", "minimum": 0.0},
                            "currency": {"type": "string", "default": "USD"}
                        },
                        "required": ["lead"]
                    },
                    "CRMDealInput": {
                        "properties": {
                            "deal_name": {"type": "string"},
                            "lead": {"type": "string"},
                            "status": {"type": "string", "enum": ["Lead", "Opportunity", "Won", "Lost"]},
                            "deal_value": {"type": "number", "minimum": 0.0},
                            "expected_deal_value": {"type": "number", "minimum": 0.0},
                            "probability": {"type": "number", "minimum": 0.0, "maximum": 100.0},
                            "lost_reason": {"type": "string", "enum": ["Price", "Competitor", "Feature Gap", "Other"]},
                            "lost_notes": {"type": "string"}
                        },
                        "required": ["status"]
                    }
                }
            }
        }

    def generate_bva_for_number(
        self,
        field_name: str,
        min_val: float = 0.0,
        max_val: float = None,
        epsilon: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Generates 3-Point BVA test cases around minimum and maximum boundaries:
        - Around min_val: min_val - epsilon (Invalid), min_val (Boundary Valid), min_val + epsilon (Valid)
        - If max_val exists: max_val - epsilon (Valid), max_val (Boundary Valid), max_val + epsilon (Invalid)
        """
        cases = []
        # Min boundary (e.g. 0.0)
        cases.append({
            "field": field_name,
            "test_type": "BVA_MIN_BELOW",
            "value": round(min_val - epsilon, 4),
            "expected_valid": False,
            "description": f"{field_name} just below minimum boundary ({min_val - epsilon})"
        })
        cases.append({
            "field": field_name,
            "test_type": "BVA_MIN_EXACT",
            "value": round(min_val, 4),
            "expected_valid": True,
            "description": f"{field_name} exact minimum boundary ({min_val})"
        })
        cases.append({
            "field": field_name,
            "test_type": "BVA_MIN_ABOVE",
            "value": round(min_val + epsilon, 4),
            "expected_valid": True,
            "description": f"{field_name} just above minimum boundary ({min_val + epsilon})"
        })

        if max_val is not None:
            cases.append({
                "field": field_name,
                "test_type": "BVA_MAX_BELOW",
                "value": round(max_val - epsilon, 4),
                "expected_valid": True,
                "description": f"{field_name} just below maximum boundary ({max_val - epsilon})"
            })
            cases.append({
                "field": field_name,
                "test_type": "BVA_MAX_EXACT",
                "value": round(max_val, 4),
                "expected_valid": True,
                "description": f"{field_name} exact maximum boundary ({max_val})"
            })
            cases.append({
                "field": field_name,
                "test_type": "BVA_MAX_ABOVE",
                "value": round(max_val + epsilon, 4),
                "expected_valid": False,
                "description": f"{field_name} just above maximum boundary ({max_val + epsilon})"
            })

        return cases

    def generate_equivalence_partitions_for_currency(self, field_name: str) -> List[Dict[str, Any]]:
        """Generates Equivalence Partitions for financial/currency fields."""
        return [
            {
                "partition": "LARGE_NEGATIVE",
                "field": field_name,
                "value": -100000.0,
                "expected_valid": False,
                "description": "Large negative currency amount"
            },
            {
                "partition": "SMALL_NEGATIVE",
                "field": field_name,
                "value": -0.01,
                "expected_valid": False,
                "description": "Smallest negative fractional currency"
            },
            {
                "partition": "ZERO_BOUNDARY",
                "field": field_name,
                "value": 0.0,
                "expected_valid": True,
                "description": "Zero nominal currency amount"
            },
            {
                "partition": "TYPICAL_POSITIVE",
                "field": field_name,
                "value": 25000.0,
                "expected_valid": True,
                "description": "Standard business positive currency value"
            },
            {
                "partition": "LARGE_ENTERPRISE_POSITIVE",
                "field": field_name,
                "value": 5000000.0,
                "expected_valid": True,
                "description": "High-value enterprise currency value"
            }
        ]

    def generate_lead_conversion_payloads(self) -> List[Dict[str, Any]]:
        """Generates combinatorial test payloads for the Convert Lead endpoint."""
        payloads = [
            # Happy path
            {
                "case_id": "GEN-LC-01",
                "category": "Happy Path",
                "payload": {"lead": "CRM-LEAD-2026-00001", "deal_value": 45000.0, "currency": "USD"},
                "expected_status": 200,
                "expected_error": None
            },
            # Missing mandatory lead
            {
                "case_id": "GEN-LC-02",
                "category": "Schema Violation",
                "payload": {"deal_value": 45000.0, "currency": "USD"},
                "expected_status": 404,
                "expected_error": "Lead None not found"
            },
            # BVA negative deal value
            {
                "case_id": "GEN-LC-03",
                "category": "BVA Violation",
                "payload": {"lead": "CRM-LEAD-2026-00001", "deal_value": -0.01, "currency": "USD"},
                "expected_status": 400,
                "expected_error": "Deal value cannot be negative"
            },
            # BVA exact zero deal value
            {
                "case_id": "GEN-LC-04",
                "category": "BVA Valid Boundary",
                "payload": {"lead": "CRM-LEAD-2026-00001", "deal_value": 0.0, "currency": "USD"},
                "expected_status": 200,
                "expected_error": None
            },
            # Large enterprise value
            {
                "case_id": "GEN-LC-05",
                "category": "EP High Positive",
                "payload": {"lead": "CRM-LEAD-2026-00001", "deal_value": 15000000.0, "currency": "USD"},
                "expected_status": 200,
                "expected_error": None
            }
        ]
        return payloads

    def generate_deal_status_payloads(self) -> List[Dict[str, Any]]:
        """Generates test payloads for Deal creation and status transitions based on BR-02/BR-03."""
        payloads = [
            # Transition to Won
            {
                "case_id": "GEN-DS-01",
                "category": "Lifecycle Valid",
                "payload": {"status": "Won", "deal_value": 30000.0},
                "expected_status": 200,
                "expected_error": None
            },
            # Transition to Lost with valid standard reason
            {
                "case_id": "GEN-DS-02",
                "category": "BR-02 Valid Lost Reason",
                "payload": {"status": "Lost", "lost_reason": "Price", "deal_value": 30000.0},
                "expected_status": 200,
                "expected_error": None
            },
            # Transition to Lost with missing reason
            {
                "case_id": "GEN-DS-03",
                "category": "BR-02 Violation Missing Reason",
                "payload": {"status": "Lost", "deal_value": 30000.0},
                "expected_status": 400,
                "expected_error": "Lost reason is mandatory when status is Lost"
            },
            # Transition to Lost with Other but missing notes
            {
                "case_id": "GEN-DS-04",
                "category": "BR-02 Violation Missing Other Notes",
                "payload": {"status": "Lost", "lost_reason": "Other", "lost_notes": "", "deal_value": 30000.0},
                "expected_status": 400,
                "expected_error": "Lost notes are mandatory when lost reason is Other"
            },
            # Transition to Lost with Other and valid notes
            {
                "case_id": "GEN-DS-05",
                "category": "BR-02 Valid Other With Notes",
                "payload": {
                    "status": "Lost",
                    "lost_reason": "Other",
                    "lost_notes": "Project delayed due to internal restructuring",
                    "deal_value": 30000.0
                },
                "expected_status": 200,
                "expected_error": None
            },
            # Negative currency rejection on update (BR-01)
            {
                "case_id": "GEN-DS-06",
                "category": "BR-01 Boundary Negative Rejection",
                "payload": {"deal_value": -0.01},
                "expected_status": 400,
                "expected_error": "deal_value cannot be negative"
            }
        ]
        return payloads

    def _get_schema_property(self, schema_name: str, property_name: str) -> Dict[str, Any]:
        """Extracts field properties and constraints dynamically from OpenAPI schema."""
        schemas = self.spec.get("components", {}).get("schemas", {})
        schema = schemas.get(schema_name, {})
        props = schema.get("properties", {})
        return props.get(property_name, {})

    def generate_all(self, output_file: str = "tests/team/data/generated_api_payloads.json") -> Dict[str, Any]:
        """Orchestrates generation of all datasets dynamically extracted from OpenAPI spec and saves to JSON."""
        deal_props = self._get_schema_property("CRMDealInput", "deal_value")
        prob_props = self._get_schema_property("CRMDealInput", "probability")

        deal_min = float(deal_props.get("minimum", 0.0))
        prob_min = float(prob_props.get("minimum", 0.0))
        prob_max = float(prob_props.get("maximum", 100.0)) if "maximum" in prob_props else None

        dataset = {
            "metadata": {
                "specification": self.spec_path,
                "generator": "OpenAPIDataGenerator",
                "version": "2.0.0",
                "standards": ["OpenAPI 3.0", "3-Point BVA", "Equivalence Partitioning", "Combinatorial"]
            },
            "bva_currency": self.generate_bva_for_number("deal_value", min_val=deal_min, epsilon=0.01),
            "bva_probability": self.generate_bva_for_number("probability", min_val=prob_min, max_val=prob_max, epsilon=0.1),
            "ep_currency": self.generate_equivalence_partitions_for_currency("deal_value"),
            "lead_conversion_cases": self.generate_lead_conversion_payloads(),
            "deal_status_cases": self.generate_deal_status_payloads()
        }

        out_dir = os.path.dirname(output_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        return dataset


if __name__ == "__main__":
    generator = OpenAPIDataGenerator()
    data = generator.generate_all()
    print(f"Generated {len(data['bva_currency'])} BVA currency cases")
    print(f"Generated {len(data['bva_probability'])} BVA probability cases")
    print(f"Generated {len(data['ep_currency'])} EP currency cases")
    print(f"Generated {len(data['lead_conversion_cases'])} Lead Conversion cases")
    print(f"Generated {len(data['deal_status_cases'])} Deal Status cases")
