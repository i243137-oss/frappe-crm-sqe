"""
Synthetic Deal Factory.
Provides builders and fixtures to generate realistic test Deals for Unit and Integration testing.
"""

import uuid
from typing import Any, Dict


def build_synthetic_deal(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    uid = uuid.uuid4().hex[:6]
    data = {
        "doctype": "CRM Deal",
        "name": f"DEAL-{uid}",
        "lead": None,
        "organization": f"Enterprise Corp {uid}",
        "status": "Qualification",
        "deal_owner": "rep@example.com",
        "deal_value": 25000.0,
        "expected_deal_value": 25000.0,
        "probability": 10,
        "currency": "USD",
        "annual_revenue": 500000.0,
        "contacts": [],
        "status_change_log": [],
    }
    if overrides:
        data.update(overrides)
    return data


def build_won_deal(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    d = {
        "status": "Won",
        "probability": 100,
    }
    if overrides:
        d.update(overrides)
    return build_synthetic_deal(d)


def build_lost_deal(lost_reason: str = None, lost_notes: str = None, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    d = {
        "status": "Lost",
        "lost_reason": lost_reason,
        "lost_notes": lost_notes,
    }
    if overrides:
        d.update(overrides)
    return build_synthetic_deal(d)
