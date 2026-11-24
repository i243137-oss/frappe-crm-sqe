"""
Mutation Testing Engine for Frappe CRM Core Business Rules.
Directly targets executable logic in:
- crm/crm/fcrm/doctype/crm_deal/crm_deal.py
- crm/crm/fcrm/doctype/crm_lead/crm_lead.py
- tests/team/fixtures/mock_frappe.py

Synthesizes 16 precise AST-level mutants across:
1. BR-01: Non-negative currency boundaries
2. BR-02: Lost Reason and Lost Notes compound condition (MCC / MC/DC)
3. BR-03: Deal Won automation (closed_date & probability)
4. BR-04: Lead conversion idempotency & eligibility gates
"""

import os
import sys
import subprocess
from typing import Dict, Any, List

MUTATION_SPECS = [
    {
        "id": "MUT-01",
        "description": "BR-01 Deal Value Boundary: Reject 0.0 currency boundary (`< 0` -> `<= 0`)",
        "file": "tests/team/fixtures/mock_frappe.py",
        "target": "if val is not None and isinstance(val, (int, float)) and val < 0:",
        "replacement": "if val is not None and isinstance(val, (int, float)) and val <= 0:",
        "test_target": "tests/team/unit/test_business_rules_and_boundaries.py"
    },
    {
        "id": "MUT-02",
        "description": "BR-01 Deal Value Inversion: Invert negative check (`< 0` -> `> 0`)",
        "file": "tests/team/fixtures/mock_frappe.py",
        "target": "if val is not None and isinstance(val, (int, float)) and val < 0:",
        "replacement": "if val is not None and isinstance(val, (int, float)) and val > 0:",
        "test_target": "tests/team/unit/test_business_rules_and_boundaries.py"
    },
    {
        "id": "MUT-03",
        "description": "BR-02 Lost Reason Guard: Invert Lost check (`== 'Lost'` -> `!= 'Lost'`)",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": 'frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost"',
        "replacement": 'frappe.get_cached_value("CRM Deal Status", self.status, "type") != "Lost"',
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-04",
        "description": "BR-02 Lost Reason Mandatory Check: Negate condition (`not self.lost_reason` -> `self.lost_reason`)",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": "if not self.lost_reason:",
        "replacement": "if self.lost_reason:",
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-05",
        "description": "BR-02 Logical AND Mutation: Mutate `and` to `or` in lost notes check",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": 'self.lost_reason == "Other" and not self.lost_notes',
        "replacement": 'self.lost_reason == "Other" or not self.lost_notes',
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-06",
        "description": "BR-02 Equality Mutation: Mutate `== 'Other'` to `!= 'Other'`",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": 'self.lost_reason == "Other"',
        "replacement": 'self.lost_reason != "Other"',
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-07",
        "description": "BR-03 Won Automation Date Setting: Replace nowdate() with None",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": "self.closed_date = frappe.utils.nowdate()",
        "replacement": "self.closed_date = '2000-01-01'",
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-08",
        "description": "BR-03 Won Default Probability: Probability assigned 0 instead of master default",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": 'self.probability = frappe.db.get_value("CRM Deal Status", self.status, "probability") or 0',
        "replacement": "self.probability = 0",
        "test_target": "tests/team/unit/test_deal_status_unit.py"
    },
    {
        "id": "MUT-09",
        "description": "BR-04 Ineligible Lead Conversion: Invert Lost check on lead conversion",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": 'frappe.get_cached_value("CRM Lead Status", lead.status, "type") == "Lost"',
        "replacement": 'frappe.get_cached_value("CRM Lead Status", lead.status, "type") != "Lost"',
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    },
    {
        "id": "MUT-10",
        "description": "BR-04 Converted Flag Setting: Set converted to 0 instead of 1",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": 'lead.db_set("converted", 1)',
        "replacement": 'lead.db_set("converted", 0)',
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    },
    {
        "id": "MUT-11",
        "description": "BR-04 Idempotency Policy Check: Mutate `if_converted == 'Fail'` to `!= 'Fail'`",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": 'if if_converted == "Fail":',
        "replacement": 'if if_converted != "Fail":',
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    },
    {
        "id": "MUT-12",
        "description": "BR-04 Return Existing Policy Check: Bypass return deal logic",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": "return deal",
        "replacement": "return None",
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    },
    {
        "id": "MUT-13",
        "description": "BR-01 Annual Revenue Boundary Mutation: `annual_revenue < 0` ignored",
        "file": "tests/team/fixtures/mock_frappe.py",
        "target": '("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total")',
        "replacement": '("deal_value", "expected_deal_value", "total", "net_total")',
        "test_target": "tests/team/unit/test_business_rules_and_boundaries.py"
    },
    {
        "id": "MUT-14",
        "description": "Audit Log Event Trigger: Suppress status change audit log record creation",
        "file": "crm/crm/fcrm/doctype/crm_deal/crm_deal.py",
        "target": "add_status_change_log(self)",
        "replacement": "pass",
        "test_target": "tests/team/unit/test_status_audit_log_unit.py"
    },
    {
        "id": "MUT-15",
        "description": "Lead Contact Linking: Suppress contact creation during conversion",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": "contact = lead.create_contact(existing_contact, False)",
        "replacement": "contact = None",
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    },
    {
        "id": "MUT-16",
        "description": "Deal Foreign Key Retention: Suppress deal.lead assignment in create_deal",
        "file": "crm/crm/fcrm/doctype/crm_lead/crm_lead.py",
        "target": '"lead": self.name',
        "replacement": '"lead": None',
        "test_target": "tests/team/unit/test_lead_conversion_unit.py"
    }
]


def run_targeted_mutation_suite() -> Dict[str, Any]:
    print(f"Beginning targeted mutation run across {len(MUTATION_SPECS)} mutants...\n")
    results = []
    killed = 0
    survived = 0

    for m in MUTATION_SPECS:
        file_path = m["file"]
        with open(file_path, "r", encoding="utf-8") as f:
            original = f.read()

        if m["target"] not in original:
            print(f"[{m['id']}] WARNING: Target pattern '{m['target'][:30]}' not found in {file_path}")
            continue

        # Apply mutation
        mutated = original.replace(m["target"], m["replacement"], 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(mutated)

        # Run specific target unit test
        cmd = [sys.executable, "-m", "pytest", m["test_target"], "-q"]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        # Restore file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original)

        if proc.returncode != 0:
            status = "KILLED"
            killed += 1
            killer = m["test_target"].split("/")[-1]
        else:
            status = "SURVIVED"
            survived += 1
            killer = "None"

        results.append({
            "id": m["id"],
            "description": m["description"],
            "status": status,
            "file": file_path,
            "killing_test": killer
        })
        print(f"[{m['id']}] {status} -> {m['description']}")

    score = round((killed / len(MUTATION_SPECS)) * 100, 2)
    return {
        "total": len(MUTATION_SPECS),
        "killed": killed,
        "survived": survived,
        "mutation_score": score,
        "mutants": results
    }


if __name__ == "__main__":
    report = run_targeted_mutation_suite()
    print("\n" + "="*60)
    print(f"FINAL MUTATION SCORE: {report['mutation_score']}% ({report['killed']}/{report['total']} killed)")
    print("="*60)
