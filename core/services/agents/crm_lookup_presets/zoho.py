from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


class ZohoCrmLookupPreset(CrmLookupPreset):
    """Zoho CRM ``Search Records`` accepts exactly one search param — ``phone``,
    ``email``, or ``word`` (full-text, used for name) — and returns matched
    records under ``data``."""

    slug = "zoho_crm"
    default_tool_name = "Search Records"
    record_path = "data"

    def build_arguments(self, field: str, value: str) -> dict:
        if field == "phone":
            param = "phone"
        elif field == "email":
            param = "email"
        elif field == "name":
            param = "word"
        else:
            raise ValueError(f"Unsupported lookup field for Zoho: {field!r}")
        return {param: value, "module": "Contacts"}
