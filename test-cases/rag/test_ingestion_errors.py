"""Unit tests for ``core.services.ingestion_errors.is_unique_violation``.

This is the seam that turns a losing concurrent-upload insert (unique
constraint hit → ``IntegrityError`` with SQLSTATE ``23505``) into a friendly
409, while letting every OTHER integrity failure (FK, NOT NULL, CHECK) bubble
up as a real 500. Getting this wrong either masks bugs or leaks 500s to users,
so we pin all three branches.
"""

from sqlalchemy.exc import IntegrityError

from core.services.ingestion_errors import is_unique_violation


class _Orig:
    def __init__(self, pgcode):
        self.pgcode = pgcode


def _integrity_error(orig):
    """Build an ``IntegrityError`` whose ``.orig`` is the given DBAPI error."""
    exc = IntegrityError("INSERT INTO knowledge_bases ...", {}, orig)
    exc.orig = orig
    return exc


def test_unique_violation_23505_is_true():
    assert is_unique_violation(_integrity_error(_Orig("23505"))) is True


def test_foreign_key_violation_23503_is_false():
    assert is_unique_violation(_integrity_error(_Orig("23503"))) is False


def test_missing_orig_is_false():
    assert is_unique_violation(_integrity_error(None)) is False
