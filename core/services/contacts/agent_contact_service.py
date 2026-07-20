"""AgentContactService — assign/list/unassign contacts on an agent (no scheduling gate).

An ``AgentContact`` row is a plain assignment: a contact is attached to an agent so the
agent's outbound flows can dial it. Assignment is idempotent (unique ``(agent_id,
contact_id)``) and can target whole directories (expanded server-side to their active
contacts) and/or explicit contact ids. Assigning does NOT schedule anything.

Context tag: ``[agent-contacts]``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.agent import Agent
from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination

_LOG_TAG = "[agent-contacts]"


class AgentContactService(BaseService):
    """Manage the contacts assigned to an agent.

    All reads/writes are org-scoped via ``BaseService.query``; the agent is verified to
    belong to the caller's org before any assignment so there is no IDOR.
    """

    # ------------------------------------------------------------------ helpers
    def _get_agent_or_404(self, agent_id: UUID) -> Agent:
        """Fetch the agent org-scoped (excludes soft-deleted) or raise 404.

        Guards every entry point so a caller can never assign/list/unassign against an
        agent outside their organization.
        """
        return self.get_or_404(Agent, agent_id, name="Agent")

    # ----------------------------------------------------------------- assign
    def assign_contacts_to_agent(
        self,
        agent_id: UUID,
        *,
        directory_ids: Optional[Sequence[UUID]] = None,
        contact_ids: Optional[Sequence[UUID]] = None,
    ) -> Dict[str, int]:
        """Assign contacts to ``agent_id`` from directories and/or explicit contact ids.

        ``directory_ids`` are expanded to their ACTIVE contact ids via
        ``ContactService.list_contact_ids_in_directories`` (the pinned shared helper),
        then unioned with ``contact_ids``. Existing ``agent_contacts`` rows are skipped
        (idempotent — unique ``(agent_id, contact_id)``). There is **no scheduling gate**.

        Returns ``{"assigned": n, "skipped": m}``.
        """
        agent = self._get_agent_or_404(agent_id)

        target_ids: set[UUID] = set(contact_ids or [])

        directory_ids = list(directory_ids or [])
        if directory_ids:
            # ContactService owns directory→contact expansion; reuse its pinned helper so
            # a whole-directory pick becomes exactly its active contacts (empty directory
            # → no ids → no-op).
            from core.services.contacts.contact_service import ContactService

            contact_service = ContactService(self.db, user_id=self._user_id, org_id=self._org_id)
            expanded = contact_service.list_contact_ids_in_directories(directory_ids)
            target_ids.update(expanded)

        if not target_ids:
            logger.info(
                f"{_LOG_TAG} assign no-op agent_id={agent_id} "
                f"directories={len(directory_ids)} — no contacts to assign"
            )
            return {"assigned": 0, "skipped": 0}

        # Only assign contacts that actually belong to this org (guards against ids from
        # another tenant sneaking in via the explicit contact_ids list).
        valid_ids = {
            row[0]
            for row in self.query(Contact)
            .filter(Contact.id.in_(target_ids), Contact.deleted_at.is_(None))
            .with_entities(Contact.id)
            .all()
        }

        already_assigned = {
            row[0]
            for row in self.db.query(AgentContact.contact_id)
            .filter(
                AgentContact.agent_id == agent.id,
                AgentContact.contact_id.in_(valid_ids),
            )
            .all()
        } if valid_ids else set()

        to_assign = valid_ids - already_assigned
        skipped = len(target_ids) - len(to_assign)

        assigned = 0
        for contact_id in to_assign:
            try:
                with self.db.begin_nested():
                    self.db.add(
                        AgentContact(
                            organization_id=self.org_id,
                            agent_id=agent.id,
                            contact_id=contact_id,
                            created_by_user_id=self.user_id,
                        )
                    )
                assigned += 1
            except IntegrityError:
                # Expected control-flow: a concurrent insert already created this
                # (agent_id, contact_id) pair; the unique constraint makes assign
                # idempotent, so skip rather than error.
                logger.debug(
                    f"{_LOG_TAG} race inserting agent_contact "
                    f"agent_id={agent.id} contact_id={contact_id}; skipping"
                )
                skipped += 1

        self.db.commit()
        logger.info(
            f"{_LOG_TAG} assigned agent_id={agent.id} "
            f"assigned={assigned} skipped={skipped}"
        )
        return {"assigned": assigned, "skipped": skipped}

    # ------------------------------------------------------------------ list
    def list_agent_contacts(
        self,
        agent_id: UUID,
        *,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Paginated list of contacts assigned to ``agent_id`` (joins contact details).

        Org-scoped and soft-delete aware. Searchable by contact name / phone; sortable by
        ``name``, ``phone_number``, or assignment ``created_at``.
        """
        agent = self._get_agent_or_404(agent_id)

        query = (
            self.query(AgentContact)
            .join(Contact, Contact.id == AgentContact.contact_id)
            .filter(
                AgentContact.agent_id == agent.id,
                Contact.deleted_at.is_(None),
            )
            .with_entities(AgentContact, Contact)
        )

        rows, total = apply_search_sort_pagination(
            query,
            search=search,
            search_fields=[Contact.name, Contact.phone_number],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "name": Contact.name,
                "phone_number": Contact.phone_number,
                "created_at": AgentContact.created_at,
            },
            page_no=page_no,
            page_size=page_size,
        )

        data = [
            {
                **contact.to_dict(),
                "assignment_id": str(assignment.id),
                "assigned_at": assignment.created_at.isoformat() if assignment.created_at else None,
            }
            for assignment, contact in rows
        ]
        return {
            "data": data,
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    # ---------------------------------------------------------------- unassign
    def unassign_contacts_from_agent(
        self, agent_id: UUID, contact_ids: Sequence[UUID]
    ) -> Dict[str, int]:
        """Remove the ``agent_contacts`` rows linking ``agent_id`` to ``contact_ids``.

        Deletes only the join rows — the contacts and their directory are untouched.
        Returns ``{"unassigned": n}`` (rows actually removed).
        """
        agent = self._get_agent_or_404(agent_id)

        ids = list(contact_ids or [])
        if not ids:
            return {"unassigned": 0}

        removed = (
            self.query(AgentContact)
            .filter(
                AgentContact.agent_id == agent.id,
                AgentContact.contact_id.in_(ids),
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        logger.info(
            f"{_LOG_TAG} unassigned agent_id={agent.id} removed={removed}"
        )
        return {"unassigned": removed}
