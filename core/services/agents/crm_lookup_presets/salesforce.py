import re

from core.services.agents.crm_lookup_presets.base import CrmLookupPreset


def _soql_escape(value: str) -> str:
    """Escape a value for inclusion inside a single-quoted SOQL string literal.

    Backslash first, then single quote (SOQL uses ``\\'``). Prevents the caller's
    spoken value from breaking out of the quoted literal."""
    return (value or "").replace("\\", "\\\\").replace("'", "\\'")


class SalesforceCrmLookupPreset(CrmLookupPreset):
    """Salesforce's hosted MCP exposes only a ``Query`` (SOQL) tool, so every
    lookup is embedded in a SOQL string: phone → ``Phone LIKE '%digits%'``,
    email → ``Email = '..'``, name → ``Name LIKE '%..%'``. Matched records are
    returned under ``records``.
    """

    slug = "salesforce"
    # Salesforce's hosted MCP (sobject-reads / sobject-all) names its SOQL tool
    # ``run_soql_query``; older/other builds may use ``query``. Resolved against
    # the server's real tools at runtime.
    default_tool_name = "run_soql_query"
    tool_name_candidates = ("run_soql_query", "query", "Query", "soql_query")
    record_path = "records"

    _SELECT = "SELECT Id, FirstName, LastName, Phone, Email FROM Contact WHERE "

    def build_arguments(self, field: str, value: str) -> dict:
        if field == "phone":
            digits = re.sub(r"\D", "", value or "")
            where = f"Phone LIKE '%{_soql_escape(digits)}%'"
        elif field == "email":
            where = f"Email = '{_soql_escape(value)}'"
        elif field == "name":
            where = f"Name LIKE '%{_soql_escape(value)}%'"
        else:
            raise ValueError(f"Unsupported lookup field for Salesforce: {field!r}")
        return {"query": f"{self._SELECT}{where} LIMIT 1"}
