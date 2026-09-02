"""Request schemas for the channel endpoints.

These mirror the fields the channel routes accepted as free-form dicts. They
are intentionally permissive: every field is optional and unknown keys are
allowed (``extra="allow"``) so clients that already send additional fields are
not rejected. The routers forward ``model_dump(exclude_unset=True)`` to the
service layer, keeping the downstream contract identical to the old dict body.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ChannelUpsertRequest(BaseModel):
    """Body for ``POST /channel/upsert``.

    ``name`` is kept optional here (rather than required) so a missing/empty
    name still produces the same ``400 Bad Request`` the router raised before,
    instead of Pydantic's ``422``. The router keeps that inline check.
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: Optional[str] = None
    channel_type: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


class ChannelListRequest(BaseModel):
    """Body for ``POST /channel/list``."""

    model_config = ConfigDict(extra="allow")

    channel_type: Optional[str] = None
    type: Optional[str] = None
