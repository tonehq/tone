"""Request schemas for the SIP trunk endpoints.

These mirror the fields the SIP trunk routes accepted as free-form dicts. They
are intentionally permissive: every field is optional and unknown keys are
allowed (``extra="allow"``) so clients that already send additional/carrier-
specific fields are not rejected. The routers forward
``model_dump(exclude_unset=True)`` to the service layer, keeping the downstream
contract identical to the old dict body — the service relies on ``"key" in
data`` to decide which columns to touch, so only fields the client actually
sent must be present.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class SipTrunkUpsertRequest(BaseModel):
    """Body for ``POST /sip/create`` and ``PUT /sip/update``.

    ``name``/``carrier`` are kept optional here (rather than required) so the
    service layer keeps raising its existing ``400`` messages instead of
    Pydantic's ``422``; create validates ``name``/``carrier`` inline.
    """

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    carrier: Optional[str] = None
    gateways: Optional[List[Any]] = None
    inbound_enabled: Optional[bool] = None
    outbound_enabled: Optional[bool] = None
    auth_mode: Optional[str] = None
    media_encryption: Optional[str] = None
    tech_prefix: Optional[str] = None
    register_enabled: Optional[bool] = None
    sip_diversion_header: Optional[bool] = None
    outbound_leading_plus_enabled: Optional[bool] = None
    number_e164_check_enabled: Optional[bool] = None
    transfer_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    auth: Optional[Any] = None


class SipAttachNumberRequest(BaseModel):
    """Body for ``POST /sip/attach_number``."""

    model_config = ConfigDict(extra="allow")

    number: Optional[str] = None
    label: Optional[str] = None
