from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


class HubSpotCrmLookupPreset(CrmLookupPreset):
    """HubSpot ``hubspot-search-objects``. Phone/email use an exact property
    filter (``CONTAINS_TOKEN`` for phone so stored-format differences still
    match; ``EQ`` for email); name uses the full-text ``query`` field (a name
    spans firstname + lastname). Matched records are returned under ``results``.
    """

    slug = "hubspot"
    default_tool_name = "hubspot-search-objects"
    tool_name_candidates = ("hubspot-search-objects", "crm_search_objects", "search_objects")
    record_path = "results"

    def build_arguments(self, field: str, value: str) -> dict:
        if field == "phone":
            return {
                "object_type": "contacts",
                "filters": [
                    {"propertyName": "phone", "operator": "CONTAINS_TOKEN", "value": value}
                ],
            }
        if field == "email":
            return {
                "object_type": "contacts",
                "filters": [
                    {"propertyName": "email", "operator": "EQ", "value": value}
                ],
            }
        if field == "name":
            return {"object_type": "contacts", "query": value}
        raise ValueError(f"Unsupported lookup field for HubSpot: {field!r}")
