"""Request schemas for the OAuth / custom-credential endpoints.

These mirror the fields the OAuth routes accepted as free-form dicts. They are
intentionally permissive: every field is optional and unknown keys are allowed
(``extra="allow"``) so clients that already send additional fields — and the
per-``auth_kind`` credential builders that read their own subset — are not
rejected. The routers forward ``model_dump(exclude_unset=True)`` to the service
layer, keeping the downstream contract identical to the old dict body (the
service still raises its own ``400`` for missing required values).
"""

from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict


class CustomCredentialRequest(BaseModel):
    """Body for ``POST /oauth/custom_credential``.

    Covers all three ``auth_kind`` builders (oauth2 client-credentials, bearer
    token, api key); each builder reads only the subset it needs.
    """

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    label: Optional[str] = None
    auth_kind: Optional[str] = None
    # oauth2_client_credentials
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[Union[str, List[str]]] = None
    scopes: Optional[Union[str, List[str]]] = None
    # bearer
    token: Optional[str] = None
    # api_key
    api_key: Optional[str] = None
    header_name: Optional[str] = None


class McpDiscoverRequest(BaseModel):
    """Body for ``POST /oauth/mcp/discover``.

    ``server_url`` stays optional so the router keeps raising its existing
    ``400 server_url is required`` instead of Pydantic's ``422``.
    """

    model_config = ConfigDict(extra="allow")

    server_url: Optional[str] = None
    label: Optional[str] = None
    return_to: Optional[str] = None
    app_integration_id: Optional[Any] = None
