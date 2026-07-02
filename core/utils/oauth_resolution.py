"""Effective OAuth-connection resolution for tools and MCP servers.

An OAuth connection can be attached at two levels:

* **Entity level** — ``tools.oauth_connection_id`` / ``mcp_servers.oauth_connection_id``
  (the default set on the Tools / MCP page).
* **Agent-version level** — ``agent_tools.oauth_connection_id`` /
  ``agent_mcp_servers.oauth_connection_id`` (set on the agent config page for
  a specific version).

Runtime picks the version-level value when set and falls back to the entity
default. This module is the single place that decides the precedence — every
resolver stamps the winner onto ``entity.effective_oauth_connection_id`` so
downstream code (handlers, header builders) reads a single attribute rather
than re-implementing the fallback.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID


EFFECTIVE_ATTR = "effective_oauth_connection_id"


def resolve_effective(link_value: Optional[UUID], entity_value: Optional[UUID]) -> Optional[UUID]:
    """Return the OAuth connection id that should actually be used.

    Precedence: agent-link override → entity default → ``None``.
    """
    return link_value or entity_value


def stamp_effective(entity, link_value: Optional[UUID]) -> None:
    """Stamp the resolved id onto ``entity.effective_oauth_connection_id``.

    Works with both ORM rows and detached rows — sets a plain attribute so
    downstream code can read the effective value without another DB round-trip.
    """
    setattr(entity, EFFECTIVE_ATTR, resolve_effective(link_value, getattr(entity, "oauth_connection_id", None)))


def effective_of(entity) -> Optional[UUID]:
    """Return ``entity.effective_oauth_connection_id`` if set, else fall back
    to ``entity.oauth_connection_id``.

    Handlers/builders that predate the override feature can migrate to this
    helper without knowing whether the caller stamped the effective value.
    """
    return getattr(entity, EFFECTIVE_ATTR, None) or getattr(entity, "oauth_connection_id", None)
