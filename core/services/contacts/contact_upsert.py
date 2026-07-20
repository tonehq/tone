"""Reusable contact upsert keyed by ``(directory_id, external_id)``.

``upsert_contact`` inserts a new ``Contact`` or updates the existing one for a directory,
returning ``(contact, action)`` where ``action`` is ``"created"`` or ``"updated"``. It
is the single write-site for the directory-scoped uniqueness rule and is shared by manual
create, multi-add, and the sync pipeline — so ``sync_id`` (and the source-of-truth fields)
are always written the same way.

It does NOT commit; the caller owns the transaction boundary (a sync commits once at the
end of a batch; a manual create commits per row).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.contact import Contact


def upsert_contact(
    db: Session,
    directory_id: UUID,
    parsed: Dict[str, Any],
    *,
    organization_id: Optional[UUID] = None,
    sync_id: Optional[UUID] = None,
    created_by_user_id: Optional[UUID] = None,
) -> Tuple[Contact, str]:
    """Insert or update a contact in ``directory_id`` keyed by ``external_id``.

    Args:
        db: the active session (the caller commits).
        directory_id: the owning directory.
        parsed: normalized contact dict — ``external_id`` (required), ``name``,
            ``phone_number``, ``contact_metadata``.
        organization_id: org to stamp on new rows (required on insert).
        sync_id: the sync run that produced this write (set when called from a sync).
        created_by_user_id: stamped on new rows.

    Returns:
        ``(contact, "created" | "updated")``. A previously soft-deleted match is revived.
    """
    external_id = parsed["external_id"]
    metadata = parsed.get("contact_metadata") or {}

    existing = (
        db.query(Contact)
        .filter(Contact.directory_id == directory_id, Contact.external_id == external_id)
        .first()
    )
    if existing is None:
        contact = Contact(
            organization_id=organization_id,
            directory_id=directory_id,
            external_id=external_id,
            name=parsed.get("name"),
            phone_number=parsed.get("phone_number"),
            contact_metadata=metadata,
            sync_id=sync_id,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )
        db.add(contact)
        return contact, "created"

    existing.name = parsed.get("name")
    existing.phone_number = parsed.get("phone_number")
    existing.contact_metadata = metadata
    if sync_id is not None:
        existing.sync_id = sync_id
    if existing.deleted_at is not None:
        # Re-importing revives a previously soft-deleted contact.
        existing.deleted_at = None
        existing.is_active = True
    return existing, "updated"
