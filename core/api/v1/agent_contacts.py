"""Agent-contacts router — assign / list / unassign contacts on an agent.

All handlers are org-scoped via ``require_org_member`` (assign/list/unassign are all
MEMBER actions per the Permissions matrix — there is no scheduling gate). Directories in
the assign body are expanded to their active contacts server-side so a whole-directory
pick is sent as one id, not thousands of rows.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.contacts.agent_contact_service import AgentContactService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AssignContactsRequest(BaseModel):
    directory_ids: Optional[List[UUID]] = Field(default=None, max_length=500)
    contact_ids: Optional[List[UUID]] = Field(default=None, max_length=1000)


class ListAgentContactsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class UnassignContactsRequest(BaseModel):
    contact_ids: List[UUID] = Field(min_length=1, max_length=1000)


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _agent_contact_service(claims: JWTClaims, db: Session) -> AgentContactService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return AgentContactService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/contacts/assign")
def assign_contacts(
    agent_id: UUID,
    body: AssignContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Assign contacts to the agent from directories and/or explicit contact ids
    (idempotent). Returns ``{assigned, skipped}``."""
    return _agent_contact_service(claims, db).assign_contacts_to_agent(
        agent_id,
        directory_ids=body.directory_ids,
        contact_ids=body.contact_ids,
    )


@router.post("/{agent_id}/contacts/list")
def list_agent_contacts(
    agent_id: UUID,
    body: ListAgentContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Paginated list of contacts assigned to the agent."""
    return _agent_contact_service(claims, db).list_agent_contacts(
        agent_id,
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.post("/{agent_id}/contacts/unassign")
def unassign_contacts(
    agent_id: UUID,
    body: UnassignContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Remove the given contacts from the agent (contacts/directory untouched)."""
    return _agent_contact_service(claims, db).unassign_contacts_from_agent(
        agent_id, body.contact_ids
    )
