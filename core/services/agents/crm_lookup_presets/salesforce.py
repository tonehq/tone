import re

from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


class SalesforceCrmLookupPreset(CrmLookupPreset):
    """Salesforce's hosted MCP exposes only a ``Query`` (SOQL) tool — no plain
    phone argument — so the phone is embedded in a SOQL string. We strip the
    phone to digits and match with ``LIKE '%digits%'`` so formatting/country-code
    differences still match. Matched records are returned under ``records``.
    """

    slug = "salesforce"
    default_tool_name = "Query"
    record_path = "records"

    def build_arguments(self, phone: str) -> dict:
        digits = re.sub(r"\D", "", phone or "")
        soql = (
            "SELECT Id, FirstName, LastName, Phone, Email "
            f"FROM Contact WHERE Phone LIKE '%{digits}%' LIMIT 1"
        )
        return {"query": soql}
