"""Scope workflows to agents and split shared workflows per agent

Adds workflows.agent_id (nullable FK to agents; NULL = legacy org-level row) so
each agent owns its workflows and every agent version keeps an independent copy.

Backfill:
- A live workflow referenced by exactly one agent gets that agent's id.
- A workflow shared by several agents stays with the agent whose referencing
  config is oldest; every other agent gets a deep copy (workflow row + draft and
  current published version rows) and its live configs are repointed to the copy.
  Encrypted graph secrets are copied verbatim (same org-level AES key).
- Unreferenced workflows keep agent_id NULL.

The org+name partial unique index is narrowed to legacy rows only
(agent_id IS NULL) because per-agent-version copies intentionally share names.

Revision ID: e2d8b4a7c9f1
Revises: e9c4b7a1d3f8
Create Date: 2026-07-02

Note: chained on top of the dev tools/MCP head (e9c4b7a1d3f8) rather than
b7c3f1a9d2e4 directly, so the workflow chain stays linear with dev and no
separate merge-heads migration is needed. e9c4b7a1d3f8 already includes
b7c3f1a9d2e4 in its ancestry (via the 1b567efe78d3 merge).

"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e2d8b4a7c9f1'
down_revision = 'e9c4b7a1d3f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'workflows',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_workflows_agent_id',
        'workflows',
        'agents',
        ['agent_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_workflows_agent_id', 'workflows', ['agent_id'])

    # Narrow the name-uniqueness index to legacy (unowned) rows BEFORE the
    # backfill runs. The deep-copied rows below reuse the source workflow's name
    # but set agent_id, so they must fall outside this index — otherwise the
    # copy INSERT collides with the still-live original on (organization_id, name).
    op.drop_index('uq_workflows_org_name', table_name='workflows')
    op.create_index(
        'uq_workflows_org_name',
        'workflows',
        ['organization_id', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL AND agent_id IS NULL'),
    )

    bind = op.get_bind()

    # Workflows referenced by exactly one agent: claim them for that agent.
    bind.execute(sa.text(
        """
        UPDATE workflows w
        SET agent_id = refs.agent_id
        FROM (
            SELECT ac.workflow_id, MIN(ac.agent_id::text)::uuid AS agent_id
            FROM agent_configs ac
            WHERE ac.workflow_id IS NOT NULL AND ac.deleted_at IS NULL
            GROUP BY ac.workflow_id
            HAVING COUNT(DISTINCT ac.agent_id) = 1
        ) refs
        WHERE w.id = refs.workflow_id
          AND w.agent_id IS NULL
          AND w.deleted_at IS NULL
        """
    ))

    # Workflows shared by several agents: the agent with the oldest referencing
    # config keeps the original; each other agent gets a deep copy.
    shared = bind.execute(sa.text(
        """
        SELECT ac.workflow_id, ac.agent_id,
               ROW_NUMBER() OVER (
                   PARTITION BY ac.workflow_id ORDER BY MIN(ac.created_at)
               ) AS rank
        FROM agent_configs ac
        JOIN workflows w ON w.id = ac.workflow_id
        WHERE ac.workflow_id IS NOT NULL AND ac.deleted_at IS NULL
          AND w.agent_id IS NULL AND w.deleted_at IS NULL
        GROUP BY ac.workflow_id, ac.agent_id
        HAVING COUNT(*) > 0
        """
    )).fetchall()

    keepers = {(r.workflow_id, r.agent_id) for r in shared if r.rank == 1}
    copies = [(r.workflow_id, r.agent_id) for r in shared if r.rank > 1]

    for workflow_id, agent_id in keepers:
        bind.execute(sa.text(
            "UPDATE workflows SET agent_id = :agent_id "
            "WHERE id = :wf_id AND agent_id IS NULL"
        ), {"agent_id": agent_id, "wf_id": workflow_id})

    for workflow_id, agent_id in copies:
        new_wf_id = uuid.uuid4()
        bind.execute(sa.text(
            """
            INSERT INTO workflows (
                id, organization_id, name, description, status,
                latest_version, created_by_user_id, agent_id,
                created_at, updated_at
            )
            SELECT :new_id, organization_id, name, description, status,
                   latest_version, created_by_user_id, :agent_id,
                   NOW(), NOW()
            FROM workflows WHERE id = :src_id
            """
        ), {"new_id": new_wf_id, "agent_id": agent_id, "src_id": workflow_id})

        # Copy the draft row and the currently published snapshot (if any).
        version_map = {}
        rows = bind.execute(sa.text(
            """
            SELECT wv.id
            FROM workflow_versions wv
            JOIN workflows w ON w.id = wv.workflow_id
            WHERE wv.workflow_id = :src_id AND wv.deleted_at IS NULL
              AND (wv.id = w.draft_version_id OR wv.id = w.published_version_id)
            """
        ), {"src_id": workflow_id}).fetchall()
        for row in rows:
            new_ver_id = uuid.uuid4()
            version_map[row.id] = new_ver_id
            bind.execute(sa.text(
                """
                INSERT INTO workflow_versions (
                    id, organization_id, workflow_id, version, is_draft,
                    graph, start_node_name, graph_checksum, is_valid,
                    validation_errors, published_at, created_by_user_id,
                    created_at, updated_at
                )
                SELECT :new_id, organization_id, :new_wf_id, version, is_draft,
                       graph, start_node_name, graph_checksum, is_valid,
                       validation_errors, published_at, created_by_user_id,
                       NOW(), NOW()
                FROM workflow_versions WHERE id = :src_ver_id
                """
            ), {"new_id": new_ver_id, "new_wf_id": new_wf_id, "src_ver_id": row.id})

        # Repoint draft/published pointers using the copied version ids.
        src_ptrs = bind.execute(sa.text(
            "SELECT draft_version_id, published_version_id FROM workflows WHERE id = :src_id"
        ), {"src_id": workflow_id}).fetchone()
        bind.execute(sa.text(
            "UPDATE workflows SET draft_version_id = :draft_id, "
            "published_version_id = :pub_id WHERE id = :new_wf_id"
        ), {
            "draft_id": version_map.get(src_ptrs.draft_version_id),
            "pub_id": version_map.get(src_ptrs.published_version_id),
            "new_wf_id": new_wf_id,
        })

        bind.execute(sa.text(
            """
            UPDATE agent_configs
            SET workflow_id = :new_wf_id
            WHERE agent_id = :agent_id AND workflow_id = :src_id
              AND deleted_at IS NULL
            """
        ), {"new_wf_id": new_wf_id, "agent_id": agent_id, "src_id": workflow_id})


def downgrade() -> None:
    bind = op.get_bind()

    # The upgrade may have created agent-owned copies that intentionally reuse a
    # source workflow's name. Reverting to the org-wide (organization_id, name)
    # unique index requires collapsing those duplicates first, otherwise the
    # CREATE UNIQUE INDEX below aborts. This is inherently lossy — the split can't
    # be perfectly un-done — so we keep the oldest live row per (org, name),
    # repoint any configs off the newer duplicates, and soft-delete the rest.
    bind.execute(sa.text(
        """
        UPDATE agent_configs ac
        SET workflow_id = keep.keep_id
        FROM workflows dup
        JOIN LATERAL (
            SELECT w2.id AS keep_id
            FROM workflows w2
            WHERE w2.organization_id = dup.organization_id
              AND w2.name = dup.name
              AND w2.deleted_at IS NULL
            ORDER BY w2.created_at ASC, w2.id ASC
            LIMIT 1
        ) keep ON TRUE
        WHERE ac.workflow_id = dup.id
          AND ac.deleted_at IS NULL
          AND dup.id <> keep.keep_id
        """
    ))
    bind.execute(sa.text(
        """
        UPDATE workflows w
        SET deleted_at = NOW()
        WHERE w.deleted_at IS NULL
          AND EXISTS (
              SELECT 1 FROM workflows w2
              WHERE w2.organization_id = w.organization_id
                AND w2.name = w.name
                AND w2.deleted_at IS NULL
                AND (w2.created_at < w.created_at
                     OR (w2.created_at = w.created_at AND w2.id < w.id))
          )
        """
    ))

    op.drop_index('uq_workflows_org_name', table_name='workflows')
    op.create_index(
        'uq_workflows_org_name',
        'workflows',
        ['organization_id', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.drop_index('ix_workflows_agent_id', table_name='workflows')
    op.drop_constraint('fk_workflows_agent_id', 'workflows', type_='foreignkey')
    op.drop_column('workflows', 'agent_id')
