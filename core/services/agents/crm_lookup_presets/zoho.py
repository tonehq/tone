from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


class ZohoCrmLookupPreset(CrmLookupPreset):
    """Zoho CRM ``Search Records`` takes a plain ``phone`` value and returns
    matched records under ``data``."""

    slug = "zoho_crm"
    default_tool_name = "Search Records"
    record_path = "data"

    def build_arguments(self, phone: str) -> dict:
        return {"phone": phone, "module": "Contacts"}
