"""unique (agent_id, run_number) on agent_readiness_runs

``run_number`` is a monotonic per-agent counter. Deep runs are serialised by
the rate limiter + coalesce cache, but shallow runs are not, so two concurrent
shallow reads (the agent-list badge racing the editor-load summary) can each
read the same ``MAX(run_number)`` and append the same number. This constraint
makes that collision a hard ``IntegrityError`` the persistence layer retries
against a fresh ``MAX + 1`` (see ``ReadinessPersistence.record`` /
``ReadinessService._next_run_number``) instead of silently storing a duplicate.

Pre-existing duplicates (from the old racy behaviour) would block the constraint,
so upgrade first renumbers each agent's rows to a clean, gap-free ``1..N``
ordered by their current ``run_number`` then ``computed_at`` — a cosmetic change
to a rarely-viewed counter (deep-run history only) that guarantees uniqueness.

Revision ID: f2c7a9e14b6d
Revises: f4a9c2e18b6d
Create Date: 2026-09-03

"""
from alembic import op


revision = "f2c7a9e14b6d"
down_revision = "f4a9c2e18b6d"
branch_labels = None
depends_on = None


_CONSTRAINT = "uq_readiness_runs_agent_run_number"


def upgrade() -> None:
    # Resolve any historical (agent_id, run_number) duplicates before adding the
    # constraint. Deterministic ordering (run_number, computed_at, id) so a
    # re-run is idempotent; only rows whose number actually changes are written.
    op.execute(
        """
        UPDATE agent_readiness_runs t
        SET run_number = s.rn
        FROM (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY agent_id
                       ORDER BY run_number ASC, computed_at ASC, id ASC
                   ) AS rn
            FROM agent_readiness_runs
        ) AS s
        WHERE t.id = s.id
          AND t.run_number IS DISTINCT FROM s.rn
        """
    )
    op.create_unique_constraint(
        _CONSTRAINT,
        "agent_readiness_runs",
        ["agent_id", "run_number"],
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "agent_readiness_runs", type_="unique")
