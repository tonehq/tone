from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


class HubSpotCrmLookupPreset(CrmLookupPreset):
    """HubSpot ``hubspot-search-objects`` takes a property filter, not a plain
    value. ``CONTAINS_TOKEN`` (not ``EQ``) is used for phone so stored-format
    differences (e.g. ``(443) 443-9905`` vs ``+1443…``) still match. Matched
    records are returned under ``results``.
    """

    slug = "hubspot"
    default_tool_name = "hubspot-search-objects"
    record_path = "results"

    def build_arguments(self, phone: str) -> dict:
        return {
            "object_type": "contacts",
            "filters": [
                {"propertyName": "phone", "operator": "CONTAINS_TOKEN", "value": phone}
            ],
        }
