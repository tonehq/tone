"""Reusable directory hard-delete helpers.

``summarize_directory_deletion`` counts the blast radius for the confirm modal;
``hard_delete_directory_and_children`` performs the FK-safe teardown in a single
transaction. Both are org-scoped (callers pass the resolved ``org_id``) and share the
same underlying counting query so the modal and the delete never disagree.

Delete order (FK-safe):
 1. find the directory's contacts;
 2. cancel queued dial jobs for their ``scheduled_calls`` (status='scheduled'), mark
    them 'canceled', then DELETE those scheduled_calls rows;
 3. mark the directory's pending/processing ``contact_syncs`` as 'failed' (C-3 race
    guard) BEFORE detaching;
 4. hard-DELETE agent_contacts for those contacts, then the contacts, then the
    directory's CSV datasource(s);
 5. DETACH contact_syncs (SET NULL directory_id + datasource_id) — kept for audit;
 6. KEEP org contact_schemas untouched;
 7. DELETE the directory.

Completed ``calls`` history is preserved (scheduled_calls.call_id / calls untouched).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.contact_sync import ContactSync
from core.models.datasource import Datasource
from core.models.scheduled_call import ScheduledCall


def _get_owned_directory(db: Session, org_id, directory_id: UUID) -> ContactDirectory:
    directory = (
        db.query(ContactDirectory)
        .filter(
            ContactDirectory.id == directory_id,
            ContactDirectory.organization_id == org_id,
            ContactDirectory.deleted_at.is_(None),
        )
        .first()
    )
    if directory is None:
        raise HTTPException(status_code=404, detail="Directory not found.")
    return directory


def _contact_ids(db: Session, org_id, directory_id: UUID) -> List[UUID]:
    rows = (
        db.query(Contact.id)
        .filter(
            Contact.directory_id == directory_id,
            Contact.organization_id == org_id,
        )
        .all()
    )
    return [row[0] for row in rows]


def summarize_directory_deletion(db: Session, org_id, directory_id: UUID) -> Dict:
    """Count the impact of hard-deleting ``directory_id`` for the confirm modal.

    Returns counts of rows that will be **deleted** (contacts, agent_contacts,
    scheduled_calls) and **detached** (syncs). Org contact_schemas are kept, so they are
    not counted for deletion. Raises 404 if the directory isn't org-owned.
    """
    _get_owned_directory(db, org_id, directory_id)
    contact_ids = _contact_ids(db, org_id, directory_id)

    contacts_count = len(contact_ids)
    agent_contacts_count = 0
    scheduled_calls_count = 0
    if contact_ids:
        agent_contacts_count = (
            db.query(AgentContact)
            .filter(AgentContact.contact_id.in_(contact_ids))
            .count()
        )
        scheduled_calls_count = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.contact_id.in_(contact_ids))
            .count()
        )

    syncs_to_detach = (
        db.query(ContactSync)
        .filter(
            ContactSync.directory_id == directory_id,
            ContactSync.organization_id == org_id,
        )
        .count()
    )

    return {
        "contacts": contacts_count,
        "agent_contacts": agent_contacts_count,
        "scheduled_calls": scheduled_calls_count,
        "syncs_detached": syncs_to_detach,
        "schemas_kept": True,
    }


def hard_delete_directory_and_children(db: Session, org_id, directory_id: UUID) -> Dict:
    """FK-safe hard-delete of a directory and its owned children, in one transaction.

    Cancels queued dial jobs, deletes contacts + agent_contacts + their scheduled_calls
    + the directory's CSV datasource(s), marks in-flight syncs failed then detaches all
    the directory's syncs (kept for audit), keeps org schemas, and deletes the directory.
    Returns a summary dict of everything removed/detached. Raises 404 if not org-owned.
    """
    from core.services.ingestion_queue import cancel_outbound_job

    _get_owned_directory(db, org_id, directory_id)
    contact_ids = _contact_ids(db, org_id, directory_id)

    cancelled_jobs = 0
    scheduled_deleted = 0
    jobs_to_cancel: List = []
    if contact_ids:
        # (2) Mark still-'scheduled' rows canceled and collect their queued dial jobs to
        # cancel AFTER commit, then delete all the directory's scheduled_calls. Deferring
        # the Procrastinate cancellation until after the DB commit ensures a later
        # rollback can't leave jobs cancelled while their rows survive.
        scheduled_rows = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.contact_id.in_(contact_ids))
            .all()
        )
        for sc in scheduled_rows:
            if sc.status == "scheduled":
                sc.status = "canceled"
                if sc.queue_job_id:
                    jobs_to_cancel.append((sc.queue_job_id, sc.id))
        db.flush()
        scheduled_deleted = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.contact_id.in_(contact_ids))
            .delete(synchronize_session=False)
        )

    # (3) C-3 race guard: mark pending/processing syncs failed BEFORE detaching so a
    # worker mid-run aborts cleanly instead of upserting into a torn-down directory.
    syncs_failed = (
        db.query(ContactSync)
        .filter(
            ContactSync.directory_id == directory_id,
            ContactSync.organization_id == org_id,
            ContactSync.status.in_(["pending", "processing"]),
        )
        .update(
            {ContactSync.status: "failed", ContactSync.error: "directory deleted"},
            synchronize_session=False,
        )
    )

    # (4) Hard-delete agent_contacts for those contacts, then the contacts.
    agent_contacts_deleted = 0
    contacts_deleted = 0
    if contact_ids:
        agent_contacts_deleted = (
            db.query(AgentContact)
            .filter(AgentContact.contact_id.in_(contact_ids))
            .delete(synchronize_session=False)
        )
        contacts_deleted = (
            db.query(Contact)
            .filter(Contact.id.in_(contact_ids))
            .delete(synchronize_session=False)
        )

    # (4 cont.) Delete the directory's CSV datasource(s).
    datasources_deleted = (
        db.query(Datasource)
        .filter(
            Datasource.directory_id == directory_id,
            Datasource.organization_id == org_id,
        )
        .delete(synchronize_session=False)
    )

    # (5) Detach the directory's syncs (SET NULL) — retained as audit.
    syncs_detached = (
        db.query(ContactSync)
        .filter(
            ContactSync.directory_id == directory_id,
            ContactSync.organization_id == org_id,
        )
        .update(
            {ContactSync.directory_id: None, ContactSync.datasource_id: None},
            synchronize_session=False,
        )
    )

    # (6) org contact_schemas untouched. (7) delete the directory.
    db.query(ContactDirectory).filter(
        ContactDirectory.id == directory_id,
        ContactDirectory.organization_id == org_id,
    ).delete(synchronize_session=False)

    db.commit()

    # Cancel the collected Procrastinate dial jobs AFTER commit so a rollback can never
    # leave a job cancelled while its scheduled_call row is still alive.
    for job_id, sc_id in jobs_to_cancel:
        try:
            cancel_outbound_job(job_id)
            cancelled_jobs += 1
        except Exception:
            logger.exception(
                "[contact-directory] failed to cancel dial job job_id={} scheduled_call_id={}",
                job_id, sc_id,
            )

    summary = {
        "directory_id": str(directory_id),
        "contacts_deleted": contacts_deleted,
        "agent_contacts_deleted": agent_contacts_deleted,
        "scheduled_calls_deleted": scheduled_deleted,
        "dial_jobs_cancelled": cancelled_jobs,
        "datasources_deleted": datasources_deleted,
        "syncs_marked_failed": syncs_failed,
        "syncs_detached": syncs_detached,
    }
    logger.info(
        "[contact-directory] hard-deleted directory id={} contacts={} agent_contacts={} "
        "scheduled_calls={} dial_jobs_cancelled={} datasources={} syncs_failed={} "
        "syncs_detached={}",
        directory_id, contacts_deleted, agent_contacts_deleted, scheduled_deleted,
        cancelled_jobs, datasources_deleted, syncs_failed, syncs_detached,
    )
    return summary
