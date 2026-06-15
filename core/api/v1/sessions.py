"""Session management endpoints.

* ``GET /sessions/list`` — list the caller's active devices.
* ``DELETE /sessions/{session_id}`` — log out a single device.
* ``POST /sessions/revoke-others`` — log out *every other* device. If no
  ``refresh_token`` is supplied in the body, the caller is logged out
  everywhere too.

All endpoints are scoped to the authenticated user — a session belonging
to someone else is invisible at this layer (``revoke_session_by_id``
filters by ``user_id``).
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, get_jwt_claims, jwt_manager
from core.services.session_service import SessionService

router = APIRouter()


def _resolve_session_id_from_refresh_token(token: str) -> Optional[str]:
    """Best-effort extraction of the session id (jti) from a refresh
    token. Returns ``None`` on any decode failure — callers should treat
    that as "no current session to preserve" without leaking why."""
    try:
        payload = jwt_manager.decode_refresh_token(token)
    except HTTPException:
        return None
    return payload.get("jti")


@router.get("/list")
def list_sessions(
    db: Session = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    sessions = SessionService(db).list_user_sessions(claims.user_id, active_only=True)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.delete("/{session_id}")
def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    revoked = SessionService(db).revoke_session_by_id(
        session_id, reason="user_logout", user_id=claims.user_id,
    )
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found",
        )
    db.commit()
    return {"message": "Session revoked"}


@router.post("/revoke-others")
def revoke_other_sessions(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """Revoke every active session for the caller.

    If the request body carries a ``refresh_token`` we resolve it to a
    session id and exclude it from the sweep — that's the "log out from
    all *other* devices" UX. If the body is empty we revoke everything,
    which is the "log out everywhere including this device" UX.
    """
    refresh_token = body.get("refresh_token")
    keep_session_id = (
        _resolve_session_id_from_refresh_token(refresh_token) if refresh_token else None
    )
    revoked_count = SessionService(db).revoke_all_for_user(
        claims.user_id,
        reason="user_logout_others",
        except_session_id=keep_session_id,
    )
    db.commit()
    return {"message": "Sessions revoked", "revoked_count": revoked_count}
