"""Per-CRM lookup preset contract.

Each app-integrated CRM (HubSpot / Salesforce / Zoho) exposes a differently
shaped lookup, so a single ``{phone_argument: phone}`` request doesn't fit all
three. A ``CrmLookupPreset`` knows, for one CRM slug: which tool to call, how to
place the caller's phone into that tool's arguments, and where the matched
record sits in the response (the wrapper key to descend before applying a
variable's ``crm_field``).

Add a new CRM = new subclass + one line in the registry (``__init__.py``). The
enrichment loop never changes (strategy pattern — mirrors
``core/services/pipeline/turn_detection/``).
"""

from abc import ABC, abstractmethod
from typing import ClassVar

# Lookup fields a preset can search by. Layer 1 (call-start pre-fill) always uses
# "phone"; Layer 2 (mid-call find_customer tool) also uses "email" / "name".
LOOKUP_FIELDS = ("phone", "email", "name")


class CrmLookupPreset(ABC):
    #: ``app_integrations.slug`` this preset applies to (e.g. ``"hubspot"``).
    slug: ClassVar[str]
    #: Default lookup tool name (pre-filled in the UI; user may override).
    default_tool_name: ClassVar[str]
    #: Wrapper key the matched record(s) sit under in the tool's response, so a
    #: variable's ``crm_field`` is written relative to the record. ``""`` = the
    #: response is already the record (no wrapper).
    record_path: ClassVar[str] = ""

    @abstractmethod
    def build_arguments(self, field: str, value: str) -> dict:
        """Shape a lookup ``value`` into this tool's argument dict.

        ``field`` is one of :data:`LOOKUP_FIELDS` (``phone`` / ``email`` /
        ``name``). Implementations raise ``ValueError`` for an unsupported field.
        """
        ...
