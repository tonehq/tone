"""Registry + factory for per-CRM lookup presets.

Keyed by ``app_integrations.slug``. A slug with no preset (a custom/other MCP)
returns ``None`` — the caller then falls back to the generic
``{phone_argument: phone}`` flow, so existing behavior is preserved.

Add a CRM = new subclass file + one entry in ``_PRESETS`` (mirrors
``core/services/pipeline/turn_detection/factory.py``).
"""

from typing import Dict, Optional

from core.services.agents.crm_lookup_presets.base import CrmLookupPreset
from core.services.agents.crm_lookup_presets.hubspot import HubSpotCrmLookupPreset
from core.services.agents.crm_lookup_presets.salesforce import SalesforceCrmLookupPreset
from core.services.agents.crm_lookup_presets.zoho import ZohoCrmLookupPreset

_PRESETS: Dict[str, CrmLookupPreset] = {
    cls.slug: cls()
    for cls in (HubSpotCrmLookupPreset, SalesforceCrmLookupPreset, ZohoCrmLookupPreset)
}


def get_crm_lookup_preset(slug: Optional[str]) -> Optional[CrmLookupPreset]:
    """Preset for a CRM slug, or ``None`` for an unknown/custom MCP (generic flow)."""
    if not slug:
        return None
    return _PRESETS.get(slug)


def has_crm_lookup_preset(slug: Optional[str]) -> bool:
    return get_crm_lookup_preset(slug) is not None
