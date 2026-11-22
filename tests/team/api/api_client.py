"""
Unified API Client for Integration & API Testing.
Seamlessly routes to a live Frappe HTTP server (when BASE_URL is reachable)
or executes against the high-fidelity mock Frappe RPC/REST handler.
"""

import os
from typing import Any, Dict, Optional
import requests

from tests.team.fixtures.mock_frappe import (
    mock_db,
    session,
    set_user,
    has_permission,
    ValidationError,
    PermissionError,
    NonNegativeError,
    MandatoryError,
)
from crm.fcrm.doctype.crm_lead.crm_lead import CRMLead, convert_to_deal
from crm.fcrm.doctype.crm_deal.crm_deal import CRMDeal, create_deal


class APIResponse:
    def __init__(self, status_code: int, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or str(json_data)

    def json(self) -> Dict[str, Any]:
        return self._json

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class FrappeAPIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("BASE_URL", "http://localhost:8000")
        self.headers = {"Content-Type": "application/json"}
        self._use_live = self._check_live()

    def _check_live(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/method/ping", timeout=0.5)
            return r.status_code == 200
        except Exception:
            return False

    def post(self, endpoint: str, data: Dict[str, Any] = None) -> APIResponse:
        data = data or {}
        if self._use_live:
            try:
                res = requests.post(f"{self.base_url}{endpoint}", json=data, headers=self.headers)
                return APIResponse(res.status_code, res.json() if res.text else {}, res.text)
            except Exception as e:
                return APIResponse(500, {"error": str(e)}, str(e))
        return self._simulate_post(endpoint, data)

    def put(self, endpoint: str, data: Dict[str, Any] = None) -> APIResponse:
        data = data or {}
        if self._use_live:
            try:
                res = requests.put(f"{self.base_url}{endpoint}", json=data, headers=self.headers)
                return APIResponse(res.status_code, res.json() if res.text else {}, res.text)
            except Exception as e:
                return APIResponse(500, {"error": str(e)}, str(e))
        return self._simulate_put(endpoint, data)

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> APIResponse:
        params = params or {}
        if self._use_live:
            try:
                res = requests.get(f"{self.base_url}{endpoint}", params=params, headers=self.headers)
                return APIResponse(res.status_code, res.json() if res.text else {}, res.text)
            except Exception as e:
                return APIResponse(500, {"error": str(e)}, str(e))
        return self._simulate_get(endpoint, params)

    def delete(self, endpoint: str) -> APIResponse:
        if self._use_live:
            try:
                res = requests.delete(f"{self.base_url}{endpoint}", headers=self.headers)
                return APIResponse(res.status_code, res.json() if res.text else {}, res.text)
            except Exception as e:
                return APIResponse(500, {"error": str(e)}, str(e))
        return self._simulate_delete(endpoint)

    # -----------------------------------------------------------------------
    # In-Process API Simulation Handlers
    # -----------------------------------------------------------------------

    def _simulate_post(self, endpoint: str, data: Dict[str, Any]) -> APIResponse:
        # 1. Lead Conversion RPC
        if endpoint == "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal":
            lead_name = data.get("lead")
            if not lead_name or not mock_db.exists("CRM Lead", lead_name):
                return APIResponse(404, {"exc_type": "DoesNotExistError", "message": f"Lead {lead_name} not found"})

            # Currency boundary validation on optional deal payload or top-level params
            deal_payload = data.get("deal") if isinstance(data.get("deal"), dict) else data
            for field in ("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total"):
                if field in deal_payload and deal_payload[field] is not None and deal_payload[field] < 0:
                    return APIResponse(400, {"exc_type": "NonNegativeError", "message": f"{field} cannot be negative"})

            try:
                deal_name = convert_to_deal(
                    lead=lead_name,
                    deal=data.get("deal"),
                    existing_contact=data.get("existing_contact"),
                    existing_organization=data.get("existing_organization"),
                    if_converted=data.get("if_converted", "Create"),
                )
                return APIResponse(200, {"message": deal_name})
            except PermissionError as e:
                return APIResponse(403, {"exc_type": "PermissionError", "message": str(e)})
            except ValidationError as e:
                return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})
            except Exception as e:
                return APIResponse(500, {"exc_type": type(e).__name__, "message": str(e)})

        # 2. Set Value RPC (used by Frappe UI for single-field updates)
        if endpoint == "/api/method/frappe.client.set_value":
            doctype = data.get("doctype")
            name = data.get("name")
            fieldname = data.get("fieldname")
            value = data.get("value")

            if not mock_db.exists(doctype, name):
                return APIResponse(404, {"message": f"{doctype} {name} not found"})

            doc = mock_db.get_doc(doctype, name)
            if not has_permission(doctype, "write", doc):
                return APIResponse(403, {"exc_type": "PermissionError", "message": "Not permitted"})

            # Promote to class for validation
            if doctype == "CRM Deal":
                target = CRMDeal(doc._data)
                target._doc_before_save = doc
                if isinstance(fieldname, dict):
                    target.update(fieldname)
                else:
                    target.set(fieldname, value)

                # Check currency boundary
                for f in ("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total"):
                    if target.get(f) is not None and target.get(f) < 0:
                        return APIResponse(400, {"exc_type": "NonNegativeError", "message": f"{f} cannot be negative"})

                try:
                    target.save()
                    return APIResponse(200, {"message": target.as_dict()})
                except ValidationError as e:
                    return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})

        # 3. REST Resource POST: /api/resource/{doctype}
        if endpoint.startswith("/api/resource/"):
            doctype = endpoint.replace("/api/resource/", "").strip("/")
            # Check currency boundary
            for f in ("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total"):
                if f in data and data[f] is not None and data[f] < 0:
                    return APIResponse(400, {"exc_type": "NonNegativeError", "message": f"{f} cannot be negative"})

            if doctype == "CRM Lead":
                lead = CRMLead(data)
                try:
                    lead.insert()
                    return APIResponse(200, {"data": lead.as_dict()})
                except ValidationError as e:
                    return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})

            if doctype == "CRM Deal":
                deal = CRMDeal(data)
                try:
                    deal.insert()
                    return APIResponse(200, {"data": deal.as_dict()})
                except ValidationError as e:
                    return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})

        return APIResponse(404, {"message": f"Endpoint {endpoint} not implemented"})

    def _simulate_put(self, endpoint: str, data: Dict[str, Any]) -> APIResponse:
        # REST Resource PUT: /api/resource/{doctype}/{name}
        if endpoint.startswith("/api/resource/"):
            parts = endpoint.replace("/api/resource/", "").split("/")
            if len(parts) == 2:
                doctype, name = parts[0], parts[1]
                if not mock_db.exists(doctype, name):
                    return APIResponse(404, {"message": f"{doctype} {name} not found"})

                doc = mock_db.get_doc(doctype, name)
                if not has_permission(doctype, "write", doc):
                    return APIResponse(403, {"exc_type": "PermissionError", "message": "Not permitted"})

                # Currency boundary
                for f in ("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total"):
                    if f in data and data[f] is not None and data[f] < 0:
                        return APIResponse(400, {"exc_type": "NonNegativeError", "message": f"{f} cannot be negative"})

                if doctype == "CRM Deal":
                    deal = CRMDeal(doc._data)
                    deal._doc_before_save = doc
                    deal.update(data)
                    try:
                        deal.save()
                        return APIResponse(200, {"data": deal.as_dict()})
                    except ValidationError as e:
                        return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})

                if doctype == "CRM Lead":
                    lead = CRMLead(doc._data)
                    lead._doc_before_save = doc
                    lead.update(data)
                    try:
                        lead.save()
                        return APIResponse(200, {"data": lead.as_dict()})
                    except ValidationError as e:
                        return APIResponse(400, {"exc_type": "ValidationError", "message": str(e)})

        return APIResponse(404, {"message": f"Endpoint {endpoint} not implemented"})

    def _simulate_get(self, endpoint: str, params: Dict[str, Any]) -> APIResponse:
        # REST Resource GET: /api/resource/{doctype}/{name}
        if endpoint.startswith("/api/resource/"):
            parts = endpoint.replace("/api/resource/", "").split("/")
            if len(parts) == 2:
                doctype, name = parts[0], parts[1]
                if not mock_db.exists(doctype, name):
                    return APIResponse(404, {"message": f"{doctype} {name} not found"})
                doc = mock_db.get_doc(doctype, name)
                if not has_permission(doctype, "read", doc):
                    return APIResponse(403, {"exc_type": "PermissionError", "message": "Not permitted"})
                return APIResponse(200, {"data": doc.as_dict()})

            if len(parts) == 1:
                doctype = parts[0]
                records = mock_db.get_all(doctype)
                return APIResponse(200, {"data": records})

        return APIResponse(404, {"message": f"Endpoint {endpoint} not implemented"})

    def _simulate_delete(self, endpoint: str) -> APIResponse:
        if endpoint.startswith("/api/resource/"):
            parts = endpoint.replace("/api/resource/", "").split("/")
            if len(parts) == 2:
                doctype, name = parts[0], parts[1]
                if not mock_db.exists(doctype, name):
                    return APIResponse(404, {"message": f"{doctype} {name} not found"})
                if doctype in mock_db.tables and name in mock_db.tables[doctype]:
                    del mock_db.tables[doctype][name]
                return APIResponse(200, {"message": "ok"})
        return APIResponse(404, {"message": f"Endpoint {endpoint} not implemented"})
