"""Single place that resolves the effective log level for a call from the DB.

Precedence (most specific non-NULL wins):

    agent.log_level  >  organization.log_level  >  env LOG_LEVEL baseline  >  INFO

Only this module reads the ``log_level`` columns. It is called from ``run_bot``
(core/bot.py) once the call's agent is resolved, and the result is applied to the
process sink — so changing a row takes effect on the next call with no build or
restart.

DB-safety: a call may run in a subprocess that deliberately avoids opening a DB
connection (the prefetch/warm path reconstructs the agent as a *transient* ORM
object). Forcing an organization lookup there would trigger an expensive first
connection, so we only query the org level when the agent is a real DB-backed
(detached/persistent) instance. Never raises — any error degrades to the env
baseline so a call is never blocked by log configuration.
"""

from typing import Tuple

from loguru import logger
from sqlalchemy import inspect as sa_inspect

from core.logging import _normalize_level, resolve_level


def _is_transient(obj) -> bool:
    """True for a reconstructed (make_transient) agent — i.e. a DB-avoiding
    subprocess. Best-effort; on any inspection error assume not transient."""
    try:
        return bool(sa_inspect(obj).transient)
    except Exception:
        logger.debug("[log-level] transient inspection failed; assuming DB-backed agent")
        return False


def resolve_call_log_level(db=None, *, agent=None, org=None, org_id=None) -> Tuple[str, str]:
    """Return ``(level, source)`` where source is ``agent`` / ``organization`` /
    ``env`` / ``default``.

    Prefers values already loaded on the ``agent`` / ``org`` objects (no query).
    Falls back to a single scoped ``organizations`` lookup only when a ``db`` is
    supplied and the agent is DB-backed (not a transient prefetch reconstruction).
    """
    try:
        # 1) Agent level — always from the loaded object (never a query).
        if agent is not None:
            agent_level = _normalize_level(getattr(agent, "log_level", None))
            if agent_level:
                return agent_level, "agent"

        # 2) Organization level — from a loaded object, else a guarded query.
        if org is not None:
            org_level = _normalize_level(getattr(org, "log_level", None))
            if org_level:
                return org_level, "organization"
        else:
            if org_id is None and agent is not None:
                org_id = getattr(agent, "organization_id", None)
            may_query = (
                db is not None
                and org_id is not None
                and (agent is None or not _is_transient(agent))
            )
            if may_query:
                from core.models.organization import Organization

                val = (
                    db.query(Organization.log_level)
                    .filter(Organization.id == org_id)
                    .scalar()
                )
                org_level = _normalize_level(val)
                if org_level:
                    return org_level, "organization"
    except Exception:
        logger.exception("[log-level] DB resolution failed — falling back to env baseline")

    # 3) Env baseline > INFO default.
    return resolve_level()
