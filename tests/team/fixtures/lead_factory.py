"""
Synthetic Lead Factory.
Provides builders and fixtures to generate realistic test Leads for Unit and Integration testing.
"""

import uuid
from typing import Any, Dict


def build_synthetic_lead(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    uid = uuid.uuid4().hex[:6]
    data = {
        "doctype": "CRM Lead",
        "name": f"LEAD-{uid}",
        "first_name": f"TestUser_{uid}",
        "last_name": "Engineer",
        "salutation": "Mr",
        "email": f"testuser_{uid}@example.com",
        "mobile_no": "+1-555-0199",
        "organization": f"Enterprise Corp {uid}",
        "status": "New",
        "lead_owner": "rep@example.com",
        "annual_revenue": 100000.0,
        "converted": 0,
        "territory": "United States",
        "industry": "Technology",
    }
    if overrides:
        data.update(overrides)
    return data


def build_lost_lead(lost_reason: str = "Price too high", lost_notes: str = None) -> Dict[str, Any]:
    return build_synthetic_lead({
        "status": "Lost",
        "lost_reason": lost_reason,
        "lost_notes": lost_notes,
    })


def build_converted_lead(linked_deal: str = "DEAL-EXISTING-01") -> Dict[str, Any]:
    return build_synthetic_lead({
        "status": "Qualified",
        "converted": 1,
    })
