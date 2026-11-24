"""
High-fidelity Mock Frappe Environment for White-Box Unit Testing.
Provides Frappe Document model, exception hierarchy, in-memory DB, QueryBuilder mock,
and session context so that Frappe CRM business logic can be tested natively and isolatedly.
"""

import sys
import types
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Frappe Exception Hierarchy
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    pass

class PermissionError(Exception):
    pass

class NonNegativeError(ValidationError):
    pass

class MandatoryError(ValidationError):
    pass

class UniqueValidationError(ValidationError):
    pass

class DoesNotExistError(ValidationError):
    pass


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _(text: str) -> str:
    """Mock translation function."""
    return text

def bold(text: str) -> str:
    return f"<b>{text}</b>"

def nowdate() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def get_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return datetime.now()

def add_to_date(dt: datetime, minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    import datetime as dtm
    delta = dtm.timedelta(minutes=minutes, hours=hours, days=days)
    return dt + delta

def validate_email_address(email: str, throw: bool = True) -> bool:
    if not email or "@" not in email:
        if throw:
            raise ValidationError(f"Invalid Email Address: {email}")
        return False
    return True


# ---------------------------------------------------------------------------
# Mock QueryBuilder
# ---------------------------------------------------------------------------

class QBField:
    def __init__(self, name: str):
        self.name = name

    def isin(self, other):
        return self

    def __eq__(self, other):
        return self

    def __ne__(self, other):
        return self

    def __or__(self, other):
        return self

    def __and__(self, other):
        return self

    def get_sql(self, **kwargs):
        return "1=1"


class QBTable:
    def __init__(self, name: str):
        self.doctype_name = name

    def __getattr__(self, item: str):
        return QBField(f"{self.doctype_name}.{item}")

    def __getitem__(self, item: str):
        return QBField(f"{self.doctype_name}.{item}")

    def as_(self, alias: str):
        return self


class QBQuery:
    def __init__(self, table: Any):
        self.table = table
        self._where = []
        self._select = []

    def select(self, *fields):
        self._select.extend(fields)
        return self

    def where(self, condition):
        self._where.append(condition)
        return self

    def for_update(self):
        return self

    def limit(self, n: int):
        return self

    def run(self):
        return [{"name": "test-record"}]

    def get_sql(self, **kwargs):
        return "1=1"


class QueryBuilderMock:
    def DocType(self, name: str):
        return QBTable(name)

    def from_(self, table: Any):
        return QBQuery(table)


# ---------------------------------------------------------------------------
# Mock Document & Metadata
# ---------------------------------------------------------------------------

class DocField:
    def __init__(self, fieldname: str, fieldtype: str = "Data", label: str = ""):
        self.fieldname = fieldname
        self.fieldtype = fieldtype
        self.label = label or fieldname
        self.name = fieldname
        self.parent = ""

    def get(self, key, default=None):
        return getattr(self, key, default)


class DocMeta:
    def __init__(self, doctype: str):
        self.doctype = doctype
        self.fields: List[DocField] = [
            DocField("name", "Data"),
            DocField("status", "Link"),
            DocField("lead_owner", "Link"),
            DocField("deal_owner", "Link"),
            DocField("organization", "Link"),
            DocField("organization_name", "Data"),
            DocField("lead", "Link"),
            DocField("deal_value", "Currency"),
            DocField("expected_deal_value", "Currency"),
            DocField("annual_revenue", "Currency"),
            DocField("total", "Currency"),
            DocField("net_total", "Currency"),
            DocField("lost_reason", "Link"),
            DocField("lost_notes", "Text"),
            DocField("closed_date", "Date"),
            DocField("probability", "Percent"),
            DocField("converted", "Check"),
            DocField("email", "Data"),
            DocField("website", "Data"),
            DocField("territory", "Link"),
            DocField("industry", "Link"),
            DocField("no_of_employees", "Literal"),
            DocField("first_name", "Data"),
            DocField("last_name", "Data"),
            DocField("salutation", "Link"),
            DocField("middle_name", "Data"),
            DocField("gender", "Link"),
            DocField("job_title", "Data"),
            DocField("mobile_no", "Data"),
            DocField("phone", "Data"),
        ]

    def has_field(self, fieldname: str) -> bool:
        return any(f.fieldname == fieldname for f in self.fields)

    def get(self, key, default=None):
        if key == "fields":
            if isinstance(default, dict):
                return [f for f in self.fields if all(getattr(f, k, None) == v for k, v in default.items())]
            return self.fields
        return default


class Flags:
    def __init__(self):
        self.ignore_permissions = False
        self.ignore_mandatory = False
        self.ignore_email_validation = False
        self._flags: Dict[str, Any] = {}

    def get(self, key, default=None):
        return getattr(self, key, self._flags.get(key, default))

    def set(self, key, value):
        setattr(self, key, value)
        self._flags[key] = value


class Document:
    """Base Frappe Document mock."""
    DOCTYPE_MAP = {
        "CRMLead": "CRM Lead",
        "CRMDeal": "CRM Deal",
        "CRMStatusChangeLog": "CRM Status Change Log",
        "CRMDealStatus": "CRM Deal Status",
        "CRMLeadStatus": "CRM Lead Status",
        "CRMLostReason": "CRM Lost Reason",
    }

    def __init__(self, dict_or_doctype: Any = None, **kwargs):
        self._data: Dict[str, Any] = {}
        self._doc_before_save: Optional["Document"] = None
        self.flags = Flags()

        if isinstance(dict_or_doctype, str):
            self.doctype = dict_or_doctype
        elif isinstance(dict_or_doctype, dict):
            self.doctype = dict_or_doctype.get("doctype", self.__class__.__name__)
            self._data.update(dict_or_doctype)
        else:
            self.doctype = self.__class__.__name__

        # Normalize DocType names
        self.doctype = self.DOCTYPE_MAP.get(self.doctype, self.doctype)
        self.meta = DocMeta(self.doctype)

        self._data.update(kwargs)
        if "name" not in self._data:
            import uuid
            prefix = self.doctype.replace(" ", "-").upper()
            self._data["name"] = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        self._data["doctype"] = self.doctype

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def __getattr__(self, item: str) -> Any:
        if item in ("_data", "_doc_before_save", "flags", "meta", "doctype"):
            return super().__getattribute__(item)
        for cls in self.__class__.__mro__:
            if item in cls.__dict__:
                return super().__getattribute__(item)
        if item in (
            "before_insert",
            "after_insert",
            "before_validate",
            "validate",
            "before_save",
            "after_save",
            "on_update",
            "on_submit",
            "on_cancel",
        ):
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{item}'")
        return self._data.get(item, None)

    def __setattr__(self, key: str, value: Any):
        if key in ("_data", "_doc_before_save", "flags", "meta", "doctype"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key, None)

    def __setitem__(self, key: str, value: Any):
        self._data[key] = value

    def update(self, d: Dict[str, Any]):
        if isinstance(d, Document):
            d = d._data
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, list):
                    self._data[k] = [Document(item) if isinstance(item, dict) else item for item in v]
                else:
                    self._data[k] = v
        return self

    def db_set(self, fieldname: str, value: Any):
        self._data[fieldname] = value
        mock_db.set_value(self.doctype, self.name, fieldname, value)

    def has_value_changed(self, fieldname: str) -> bool:
        if not self._doc_before_save:
            return True
        return self.get(fieldname) != self._doc_before_save.get(fieldname)

    def is_new(self) -> bool:
        return self._doc_before_save is None

    def get_doc_before_save(self) -> Optional["Document"]:
        return self._doc_before_save

    def append(self, table_fieldname: str, child_dict: Dict[str, Any]):
        if table_fieldname not in self._data or not isinstance(self._data[table_fieldname], list):
            self._data[table_fieldname] = []
        child = Document(child_dict)
        self._data[table_fieldname].append(child)
        return child

    def get_assigned_users(self) -> List[str]:
        owner = self.get("deal_owner") or self.get("lead_owner")
        return [owner] if owner else []

    def assign_agent(self, agent: str):
        pass

    def share_with_agent(self, agent: str):
        pass

    def check_permission(self, permtype="read", permlevel=None):
        if not has_permission(self.doctype, permtype, self):
            throw(f"No permission to {permtype} {self.doctype} {self.name}", PermissionError)

    def validate_values(self):
        """Enforces schema-level non_negative validation matching Frappe DocType definition."""
        if self.doctype in ("CRM Deal", "CRM Lead"):
            non_negative_fields = ("deal_value", "expected_deal_value", "annual_revenue", "total", "net_total")
            for f in non_negative_fields:
                val = self._data.get(f)
                if val is not None and isinstance(val, (int, float)) and val < 0:
                    throw(f"{f} cannot be negative ({val})", NonNegativeError)

    def insert(self, ignore_permissions: bool = False):
        self.validate_values()
        if callable(getattr(self, "before_insert", None)):
            self.before_insert()
        if callable(getattr(self, "before_validate", None)):
            self.before_validate()
        if callable(getattr(self, "validate", None)):
            self.validate()
        self._doc_before_save = Document(dict(self._data))
        mock_db.save_doc(self)
        if callable(getattr(self, "after_insert", None)):
            self.after_insert()
        return self

    def save(self, ignore_permissions: bool = False):
        self.validate_values()
        if callable(getattr(self, "before_validate", None)):
            self.before_validate()
        if callable(getattr(self, "validate", None)):
            self.validate()
        if callable(getattr(self, "before_save", None)):
            self.before_save()
        self._doc_before_save = Document(dict(self._data))
        mock_db.save_doc(self)
        return self

    def reload(self):
        loaded = mock_db.get_doc(self.doctype, self.name)
        if loaded:
            self._data.update(loaded._data)
        return self

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)


# ---------------------------------------------------------------------------
# In-Memory Mock Database
# ---------------------------------------------------------------------------

class MockDatabase:
    def __init__(self):
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.single_values: Dict[str, Dict[str, Any]] = {
            "FCRM Settings": {
                "enable_forecasting": 0,
                "currency": "USD",
                "enable_sales_hierarchy": 0,
                "auto_update_expected_deal_value": 0,
            }
        }
        self.init_defaults()

    def init_defaults(self):
        self.tables["CRM Deal Status"] = {
            "Qualification": {"name": "Qualification", "type": "Open", "probability": 10},
            "Negotiation": {"name": "Negotiation", "type": "Open", "probability": 50},
            "Won": {"name": "Won", "type": "Won", "probability": 100},
            "Lost": {"name": "Lost", "type": "Lost", "probability": 0},
        }
        self.tables["CRM Lead Status"] = {
            "New": {"name": "New", "type": "Open"},
            "Open": {"name": "Open", "type": "Open"},
            "Qualified": {"name": "Qualified", "type": "Qualified"},
            "Lost": {"name": "Lost", "type": "Lost"},
        }
        self.tables["CRM Lost Reason"] = {
            "Price too high": {"name": "Price too high"},
            "Competition": {"name": "Competition"},
            "Other": {"name": "Other"},
        }
        self.tables["CRM Lead"] = {}
        self.tables["CRM Deal"] = {}
        self.tables["CRM Organization"] = {}
        self.tables["Contact"] = {}
        self.tables["Contact Email"] = {}

    def reset(self):
        self.tables.clear()
        self.single_values = {
            "FCRM Settings": {
                "enable_forecasting": 0,
                "currency": "USD",
                "enable_sales_hierarchy": 0,
                "auto_update_expected_deal_value": 0,
            }
        }
        self.init_defaults()

    def save_doc(self, doc: Document):
        doctype = doc.doctype
        if doctype not in self.tables:
            self.tables[doctype] = {}
        self.tables[doctype][doc.name] = doc.as_dict()

    def get_doc(self, doctype: str, name: str) -> Optional[Document]:
        rec = self.tables.get(doctype, {}).get(name)
        return Document(rec) if rec else None

    def exists(self, doctype: str, filters: Any = None) -> Any:
        if isinstance(filters, str):
            return filters if filters in self.tables.get(doctype, {}) else False
        if isinstance(filters, dict):
            for docname, fields in self.tables.get(doctype, {}).items():
                match = True
                for k, v in filters.items():
                    if isinstance(v, tuple) and v[0] == "!=":
                        if fields.get(k) == v[1]:
                            match = False
                            break
                    elif fields.get(k) != v:
                        match = False
                        break
                if match:
                    return docname
        return False

    def get_value(self, doctype: str, filters: Any, fieldname: str = "name") -> Any:
        if isinstance(filters, str):
            rec = self.tables.get(doctype, {}).get(filters)
            return rec.get(fieldname) if rec else None
        if isinstance(filters, dict):
            for docname, fields in self.tables.get(doctype, {}).items():
                match = True
                for k, v in filters.items():
                    if fields.get(k) != v:
                        match = False
                        break
                if match:
                    return fields.get(fieldname)
        return None

    def get_single_value(self, doctype: str, fieldname: str) -> Any:
        return self.single_values.get(doctype, {}).get(fieldname)

    def set_value(self, doctype: str, name: str, fieldname: Any, value: Any = None, update_modified: bool = True):
        if doctype in self.tables and name in self.tables[doctype]:
            if isinstance(fieldname, dict):
                self.tables[doctype][name].update(fieldname)
            else:
                self.tables[doctype][name][fieldname] = value

    def get_all(self, doctype: str, filters: Dict[str, Any] = None, fields: List[str] = None, pluck: str = None) -> List[Any]:
        results = []
        for name, data in self.tables.get(doctype, {}).items():
            if filters:
                match = all(data.get(k) == v for k, v in filters.items())
                if not match:
                    continue
            if pluck:
                results.append(data.get(pluck))
            else:
                results.append(data)
        return results


mock_db = MockDatabase()


# ---------------------------------------------------------------------------
# Session & Permissions
# ---------------------------------------------------------------------------

class Session:
    def __init__(self):
        self.user = "Administrator"


class Session:
    def __init__(self):
        self.user = "Administrator"
        self.sid = "sid_test_1234567890abcdef"
        self.csrf_token = "csrf_token_test_abc123"
        self.data = {
            "user": "Administrator",
            "session_expiry": "06:00:00",
            "full_name": "Administrator",
            "user_type": "System User",
        }


session = Session()
_permissions_override: Dict[tuple, bool] = {}
_user_roles: Dict[str, List[str]] = {
    "Administrator": ["System Manager", "Sales Manager"],
    "manager@example.com": ["Sales Manager"],
    "rep@example.com": ["Sales User"],
    "rep_a@example.com": ["Sales User"],
    "rep_b@example.com": ["Sales User"],
    "Guest": ["Guest"],
}

def set_user(user: str, roles: List[str] = None):
    session.user = user
    if user == "Guest":
        session.sid = None
        session.csrf_token = None
    else:
        session.sid = f"sid_{user.split('@')[0]}_secure_123"
        session.csrf_token = f"csrf_{user.split('@')[0]}_token"
    if roles:
        _user_roles[user] = roles

def get_roles(user: str = None) -> List[str]:
    u = user or session.user
    if u == "Guest":
        return ["Guest"]
    return _user_roles.get(u, ["Sales User"])

def set_permission_override(doctype: str, ptype: str, docname: str, user: str, allowed: bool):
    _permissions_override[(doctype, ptype, docname, user)] = allowed

def has_permission(doctype: str, ptype: str = "read", doc: Any = None, user: str = None) -> bool:
    u = user or session.user
    roles = get_roles(u)

    # 1. Guest / Anonymous users are strictly disallowed from CRM records
    if u == "Guest" or "Guest" in roles:
        return False

    # 2. Administrator & Sales Manager have global administrative CRM authority
    if "System Manager" in roles:
        return True
    if "Sales Manager" in roles:
        return True

    # 3. Explicit granular override check
    docname = doc.name if isinstance(doc, Document) else str(doc) if doc else None
    if docname:
        override = _permissions_override.get((doctype, ptype, docname, u))
        if override is not None:
            return override

    # 4. Resolve Document reference if passed as ID string
    target_doc = doc
    if isinstance(doc, str) and doctype in ("CRM Lead", "CRM Deal", "CRM Note", "CRM Call Log"):
        target_doc = mock_db.get_doc(doctype, doc)

    # 5. Row-level Ownership checks for Sales Users
    if isinstance(target_doc, Document):
        owner = target_doc.get("lead_owner") or target_doc.get("deal_owner") or target_doc.get("owner")
        if owner:
            if owner == u:
                return True
            # Attempting to write/convert/delete another user's record is denied
            if ptype in ("write", "delete", "convert"):
                return False
            # Read might be denied unless assigned
            return False
        # Unassigned lead/deal: allowed for manager, but standard sales user cannot write unassigned without manager delegation
        if ptype in ("write", "delete") and not owner:
            return True
        return True

    # Universal create permission for authenticated CRM roles
    if ptype == "create":
        return True

    return True

def throw(msg: str, exc: Any = ValidationError, title: Optional[str] = None):
    raise exc(msg)


# ---------------------------------------------------------------------------
# Setup sys.modules Mocking
# ---------------------------------------------------------------------------

def setup_mock_frappe():
    """Installs mock frappe and its submodules into sys.modules."""
    frappe_mod = types.ModuleType("frappe")
    frappe_mod.__path__ = []
    frappe_mod.ValidationError = ValidationError
    frappe_mod.PermissionError = PermissionError
    frappe_mod.NonNegativeError = NonNegativeError
    frappe_mod.MandatoryError = MandatoryError
    frappe_mod.UniqueValidationError = UniqueValidationError
    frappe_mod.DoesNotExistError = DoesNotExistError
    frappe_mod._ = _
    frappe_mod.bold = bold
    frappe_mod.throw = throw
    frappe_mod.db = mock_db
    frappe_mod.qb = QueryBuilderMock()
    frappe_mod.session = session
    frappe_mod.get_roles = get_roles
    frappe_mod.has_permission = has_permission
    frappe_mod.whitelist = lambda *args, **kwargs: (lambda f: f)
    frappe_mod.get_cached_value = mock_db.get_value
    frappe_mod.get_all = mock_db.get_all

    def get_doc(doctype_or_dict, name=None):
        if name:
            doc_data = mock_db.get_doc(doctype_or_dict, name)
            if not doc_data:
                rec = mock_db.tables.get(doctype_or_dict, {}).get(name)
                if rec:
                    doc_data = Document(rec)
            if doc_data:
                if doctype_or_dict == "CRM Lead" and "crm.fcrm.doctype.crm_lead.crm_lead" in sys.modules:
                    cls = sys.modules["crm.fcrm.doctype.crm_lead.crm_lead"].CRMLead
                    inst = cls()
                    inst._data = dict(doc_data._data)
                    inst._doc_before_save = Document(dict(doc_data._data))
                    return inst
                if doctype_or_dict == "CRM Deal" and "crm.fcrm.doctype.crm_deal.crm_deal" in sys.modules:
                    cls = sys.modules["crm.fcrm.doctype.crm_deal.crm_deal"].CRMDeal
                    inst = cls()
                    inst._data = dict(doc_data._data)
                    inst._doc_before_save = Document(dict(doc_data._data))
                    return inst
                return doc_data
            return Document(doctype=doctype_or_dict, name=name)
        if isinstance(doctype_or_dict, dict):
            return Document(doctype_or_dict)
        return Document(doctype=doctype_or_dict)

    frappe_mod.get_doc = get_doc
    frappe_mod.get_last_doc = lambda doctype, filters=None: Document(doctype=doctype)

    def new_doc(doctype):
        import uuid
        uid = uuid.uuid4().hex[:6].upper()
        if doctype == "CRM Deal" and "crm.fcrm.doctype.crm_deal.crm_deal" in sys.modules:
            cls = sys.modules["crm.fcrm.doctype.crm_deal.crm_deal"].CRMDeal
            inst = cls()
            inst.doctype = "CRM Deal"
            inst._data["doctype"] = "CRM Deal"
            inst._data["name"] = f"CRM-DEAL-{uid}"
            return inst
        if doctype == "CRM Lead" and "crm.fcrm.doctype.crm_lead.crm_lead" in sys.modules:
            cls = sys.modules["crm.fcrm.doctype.crm_lead.crm_lead"].CRMLead
            inst = cls()
            inst.doctype = "CRM Lead"
            inst._data["doctype"] = "CRM Lead"
            inst._data["name"] = f"CRM-LEAD-{uid}"
            return inst
        doc = Document(doctype=doctype)
        prefix = doctype.replace(" ", "-").upper()
        doc.doctype = doctype
        doc._data["doctype"] = doctype
        doc._data["name"] = f"{prefix}-{uid}"
        return doc

    frappe_mod.new_doc = new_doc
    frappe_mod.get_cached_doc = lambda doctype, name: get_doc(doctype, name)
    frappe_mod.only_for = lambda *args, **kwargs: True

    # Submodule: frappe.model.document
    model_doc = types.ModuleType("frappe.model.document")
    model_doc.Document = Document
    frappe_mod.model = types.ModuleType("frappe.model")
    frappe_mod.model.document = model_doc

    # Submodule: frappe.utils
    utils_mod = types.ModuleType("frappe.utils")
    utils_mod.nowdate = nowdate
    utils_mod.get_datetime = get_datetime
    utils_mod.add_to_date = add_to_date
    utils_mod.validate_email_address = validate_email_address
    frappe_mod.utils = utils_mod

    # Submodule: frappe.utils.caching
    caching_mod = types.ModuleType("frappe.utils.caching")
    caching_mod.request_cache = lambda f: f
    frappe_mod.utils.caching = caching_mod

    # Submodule: frappe.desk.form.assign_to
    desk_mod = types.ModuleType("frappe.desk")
    form_mod = types.ModuleType("frappe.desk.form")
    assign_mod = types.ModuleType("frappe.desk.form.assign_to")
    assign_mod._add = lambda *args, **kwargs: None
    assign_mod.add = lambda *args, **kwargs: None
    assign_mod.remove = lambda *args, **kwargs: None
    frappe_mod.desk = desk_mod
    frappe_mod.desk.form = form_mod
    frappe_mod.desk.form.assign_to = assign_mod

    # Submodule: frappe.share
    share_mod = types.ModuleType("frappe.share")
    share_mod.add_docshare = lambda *args, **kwargs: None
    share_mod.remove = lambda *args, **kwargs: None
    frappe_mod.share = share_mod

    # Register in sys.modules
    sys.modules["frappe"] = frappe_mod
    sys.modules["frappe.model"] = frappe_mod.model
    sys.modules["frappe.model.document"] = model_doc
    sys.modules["frappe.utils"] = utils_mod
    sys.modules["frappe.utils.caching"] = caching_mod
    sys.modules["frappe.desk"] = desk_mod
    sys.modules["frappe.desk.form"] = form_mod
    sys.modules["frappe.desk.form.assign_to"] = assign_mod
    sys.modules["frappe.share"] = share_mod

    # Stub peripheral crm modules
    for mod_name in [
        "crm.api.whatsapp",
        "crm.api.exchange_rate",
        "crm.automation.events",
        "crm.fcrm.doctype.crm_service_level_agreement.utils",
        "crm.fcrm.doctype.utils",
        "crm.domain_enrichment.tasks",
        "crm.domain_enrichment.cross_record",
        "crm.api.form",
    ]:
        m = types.ModuleType(mod_name)
        m.guard_doc_recipient_change = lambda doc: None
        m.get_exchange_rate = lambda cur, sys_cur: 1.0
        m.emit_lead_converted = lambda *args: None
        m.get_sla = lambda doc: None
        m.add_or_remove_lost_reason_section_in_sidepanel = lambda doc: None
        m.auto_enrich_on_create = lambda doc: None
        m.copy_enrichment_from_organization = lambda doc: None
        m.enrich_form_submission = lambda doc: None
        sys.modules[mod_name] = m

    return frappe_mod
