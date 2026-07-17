"""Session lifecycle service.

Owns every transition on a ``user_sessions`` row:

* ``create_session``    — at ``/login``
* ``rotate_session``    — at ``/refresh`` (replaces the refresh-token hash)
* ``revoke_session_*``  — at ``/logout``
* ``revoke_all_for_user`` — on password change / reset
* ``revoke_family``     — on detected refresh-token reuse
* ``list_user_sessions`` — for the "active devices" UI

The service is framework-agnostic; callers provide a ``DeviceContext``
(see ``core.utils.device``) when device info is relevant.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Query, Session

from core.models.user_session import UserSession
from core.services.base import BaseService
from core.utils.auth_helpers import coerce_uuid, hash_token, utcnow
from core.utils.device import DeviceContext


UUIDLike = Union[str, uuid.UUID]

# Device fields ``DeviceContext`` populates on a session row. Kept in one
# place so adding a column (e.g. ``country``) needs no service change.
_DEVICE_FIELDS = (
    "ip_address", "user_agent", "device_type", "device_name",
    "browser", "os", "country", "city",
)


# ── helpers ──────────────────────────────────────────────────────────────


def _apply_device(session: UserSession, device: Optional[DeviceContext]) -> None:
    """Copy any non-None fields from ``device`` onto the session row.

    Partial overwrite — fields the client didn't send this time keep
    their last-known value (e.g. when a proxy strips ``User-Agent``).
    """
    if not device:
        return
    for field in _DEVICE_FIELDS:
        value = getattr(device, field, None)
        if value is not None:
            setattr(session, field, value)


# ── service ──────────────────────────────────────────────────────────────


class SessionService(BaseService):
    def __init__(
        self,
        db: Session,
        user_id: Optional[UUIDLike] = None,
        org_id: Optional[UUIDLike] = None,
    ):
        super().__init__(db, user_id=user_id, org_id=org_id)

    # ── creation ──

    def create_session(
        self,
        *,
        user_id: UUIDLike,
        organization_id: Optional[UUIDLike],
        refresh_token: str,
        expires_at: datetime,
        device: Optional[DeviceContext] = None,
        session_id: Optional[UUIDLike] = None,
        family: Optional[UUIDLike] = None,
    ) -> UserSession:
        """Persist a session row.

        ``session_id`` and ``family`` may be pre-allocated by the caller so
        the refresh-token's ``jti`` / ``family`` claims match the row before
        it is written. When omitted, fresh UUIDs are generated.
        """
        uid = coerce_uuid(user_id)
        if not uid:
            raise ValueError("user_id is required to create a session")

        session = UserSession(
            id=coerce_uuid(session_id) or uuid.uuid4(),
            user_id=uid,
            organization_id=coerce_uuid(organization_id),
            refresh_token_hash=hash_token(refresh_token),
            refresh_token_family=coerce_uuid(family) or uuid.uuid4(),
            expires_at=expires_at,
        )
        _apply_device(session, device)
        self.db.add(session)
        self.db.flush()
        return session

    # ── rotation (refresh flow) ──

    def rotate_session(
        self,
        *,
        session_id: UUIDLike,
        presented_refresh_token: str,
        new_refresh_token: str,
        device: Optional[DeviceContext] = None,
    ) -> Optional[UserSession]:
        """Validate and rotate a session's refresh-token hash.

        Returns the updated session on success. Returns ``None`` if the
        session is unknown, revoked, expired, or if the presented token
        no longer matches the stored hash (rotation reuse — the whole
        family is revoked as a side effect).
        """
        sid = coerce_uuid(session_id)
        if not sid:
            return None

        session = self.db.query(UserSession).filter(UserSession.id == sid).first()
        if not session:
            return None
        if session.revoked_at is not None or session.expires_at <= utcnow():
            return None

        if session.refresh_token_hash != hash_token(presented_refresh_token):
            # Rotation reuse — token was already swapped, so this is a
            # replay of an old/leaked one. Burn the whole family.
            self.revoke_family(session.refresh_token_family, "rotation_reuse")
            return None

        session.refresh_token_hash = hash_token(new_refresh_token)
        session.last_used_at = utcnow()
        _apply_device(session, device)
        self.db.flush()
        return session

    def rotate_for_org_switch(
        self,
        *,
        session_id: UUIDLike,
        new_refresh_token: str,
        organization_id: Optional[UUIDLike],
        device: Optional[DeviceContext] = None,
    ) -> Optional[UserSession]:
        """Move a live session onto a new org and store a freshly-minted
        refresh-token hash, without requiring the old refresh token.

        Used by the org-switch flow: the caller is already authenticated via
        its access token (and membership is verified upstream), so — unlike
        ``rotate_session`` — there is no presented-token check. Returns the
        updated session, or ``None`` if it is unknown / revoked / expired.
        """
        sid = coerce_uuid(session_id)
        if not sid:
            return None
        session = self.db.query(UserSession).filter(UserSession.id == sid).first()
        if not session or session.revoked_at is not None or session.expires_at <= utcnow():
            return None
        session.refresh_token_hash = hash_token(new_refresh_token)
        session.organization_id = coerce_uuid(organization_id)
        session.last_used_at = utcnow()
        _apply_device(session, device)
        self.db.flush()
        return session

    # ── revocation ──

    def revoke_session(self, session: UserSession, reason: str) -> None:
        if session.revoked_at is not None:
            return
        session.revoked_at = utcnow()
        session.revoked_reason = reason
        self.db.flush()

    def revoke_session_by_id(
        self,
        session_id: UUIDLike,
        reason: str,
        *,
        user_id: Optional[UUIDLike] = None,
    ) -> bool:
        """Revoke a single session. Optionally scope to a user so callers
        can safely act on user-supplied session IDs without authorisation
        gymnastics."""
        sid = coerce_uuid(session_id)
        if not sid:
            return False
        q = self.db.query(UserSession).filter(
            UserSession.id == sid,
            UserSession.revoked_at.is_(None),
        )
        uid = coerce_uuid(user_id)
        if uid:
            q = q.filter(UserSession.user_id == uid)
        session = q.first()
        if not session:
            return False
        self.revoke_session(session, reason)
        return True

    def revoke_session_by_refresh_token(self, refresh_token: str, reason: str) -> bool:
        token_hash = hash_token(refresh_token)
        session = (
            self.db.query(UserSession)
            .filter(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
            .first()
        )
        if not session:
            return False
        self.revoke_session(session, reason)
        return True

    def _bulk_revoke(self, query: Query, reason: str) -> int:
        """Apply a soft-revoke to every row matched by ``query`` in one
        ``UPDATE``. ``query`` is expected to already filter to active rows."""
        count = query.update(
            {
                UserSession.revoked_at: utcnow(),
                UserSession.revoked_reason: reason,
            },
            synchronize_session=False,
        )
        self.db.flush()
        return int(count or 0)

    def revoke_all_for_user(
        self,
        user_id: UUIDLike,
        reason: str,
        *,
        except_session_id: Optional[UUIDLike] = None,
    ) -> int:
        uid = coerce_uuid(user_id)
        if not uid:
            return 0
        q = self.db.query(UserSession).filter(
            UserSession.user_id == uid,
            UserSession.revoked_at.is_(None),
        )
        except_id = coerce_uuid(except_session_id)
        if except_id:
            q = q.filter(UserSession.id != except_id)
        return self._bulk_revoke(q, reason)

    def revoke_family(self, family_id: UUIDLike, reason: str) -> int:
        family_uuid = coerce_uuid(family_id)
        if not family_uuid:
            return 0
        q = self.db.query(UserSession).filter(
            UserSession.refresh_token_family == family_uuid,
            UserSession.revoked_at.is_(None),
        )
        return self._bulk_revoke(q, reason)

    # ── queries ──

    def get_session(self, session_id: UUIDLike) -> Optional[UserSession]:
        sid = coerce_uuid(session_id)
        if not sid:
            return None
        return self.db.query(UserSession).filter(UserSession.id == sid).first()

    def list_user_sessions(
        self,
        user_id: UUIDLike,
        *,
        active_only: bool = True,
    ) -> List[UserSession]:
        uid = coerce_uuid(user_id)
        if not uid:
            return []
        q = self.db.query(UserSession).filter(UserSession.user_id == uid)
        if active_only:
            q = q.filter(
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > utcnow(),
            )
        return q.order_by(UserSession.last_used_at.desc()).all()
