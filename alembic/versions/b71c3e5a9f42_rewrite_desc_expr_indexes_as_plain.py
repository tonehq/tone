"""rewrite eval result DESC expression indexes as plain btree

Alembic autogenerate cannot round-trip functional indexes defined via
``text("run_number DESC")`` through DB reflection: the reflected column
name comes back as the literal string ``"run_number DESC"`` and the
Index reconstruction then fails with ``ArgumentError: Column(s)
'<table>.run_number DESC' are not part of table``, which blocks EVERY
autogenerate run in the repo.

Both original DESC indexes were only ever used to answer "latest N rows
for this scope" queries — a plain btree on ``(<scope>, run_number)``
serves those queries just as well because Postgres can scan the btree
backward for an ``ORDER BY run_number DESC LIMIT n`` plan. Dropping the
DESC clause removes the autogen limitation without any query-plan
regression.

Applied indexes:
- ``ix_eval_results_eval_run_desc``       on ``eval_results (eval_id, run_number)``
- ``ix_agent_llm_eval_results_agent_run_desc``
                                          on ``agent_llm_eval_results (agent_id, run_number)``

The index NAMES are kept identical so downstream code / query plans /
monitoring don't need to change; only the ordering clause is dropped.

Revision ID: b71c3e5a9f42
Revises: d8c4e2f19a3b
Create Date: 2026-08-24 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b71c3e5a9f42"
down_revision = "d8c4e2f19a3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # eval_results.
    op.drop_index("ix_eval_results_eval_run_desc", table_name="eval_results")
    op.create_index(
        "ix_eval_results_eval_run_desc",
        "eval_results",
        ["eval_id", "run_number"],
        unique=False,
    )

    # agent_llm_eval_results.
    op.drop_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        table_name="agent_llm_eval_results",
    )
    op.create_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        "agent_llm_eval_results",
        ["agent_id", "run_number"],
        unique=False,
    )


def downgrade() -> None:
    # Restore the original functional-index form. This re-introduces the
    # autogenerate hazard — downgrade only if you're rolling back the model
    # change too.
    op.drop_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        table_name="agent_llm_eval_results",
    )
    op.create_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        "agent_llm_eval_results",
        ["agent_id", sa.text("run_number DESC")],
        unique=False,
    )

    op.drop_index("ix_eval_results_eval_run_desc", table_name="eval_results")
    op.create_index(
        "ix_eval_results_eval_run_desc",
        "eval_results",
        ["eval_id", sa.text("run_number DESC")],
        unique=False,
    )
