'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { PROFILE_VAR_FLUSH_FAILED_KEY } from '@/components/agents/AgentEditorShell';
import ProfileVariableModal, {
  type ProfileVarFormValues,
} from '@/components/agents/profile-variables/ProfileVariableModal';
import CustomButton from '@/components/shared/CustomButton';
import CustomModal from '@/components/shared/CustomModal';
import CustomTable from '@/components/shared/CustomTable';
import CustomTooltip from '@/components/shared/CustomTooltip';
import {
  useAgentProfileVariables,
  useCreateAgentProfileVariable,
  useDeleteAgentProfileVariable,
  useUpdateAgentProfileVariable,
} from '@/lib/api/agentProfileVariables';
import { createAgentProfileVariable } from '@/services/agentProfileVariableService';
import type { AgentFormState, ProfileVariableDraft } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/**
 * Manages one agent's Profile variables (the `{{profile.<key>}}` placeholders).
 * Rendered inside the "Profile" sidebar step (`ProfileStep`).
 *
 * Dual-mode by design so callers don't need two components:
 * - EDIT (`agentId` present) — talks to `/agents/{id}/profile-variables` via
 *   TanStack Query hooks. Writes hit the server immediately.
 * - CREATE (`agentId` null) — buffers rows in RHF form state
 *   (`profile_variable_drafts`). `AgentEditorShell.onSubmit` flushes them
 *   after the agent is created.
 *
 * The underlying table + add / edit / delete UI is shared across modes so
 * behavior stays in lockstep — the modes only differ in which handlers are
 * wired in. (`CustomModal` is still used inside for the delete-confirm and
 * for the single-row add/edit modal.)
 */
export default function ProfileVariablesManager({ agentId }: { agentId: string | null }) {
  return agentId ? <EditModePanel agentId={agentId} /> : <CreateModePanel />;
}

/** Row shape rendered by the shared panel — unifies API rows (persisted id)
 * and draft rows (client-generated `_draftId`) so the table stays mode-agnostic. */
interface PanelRow {
  id: string;
  key: string;
  value: string;
  description: string | null;
}

// ── EDIT mode (API-backed) ──────────────────────────────────────────────

function EditModePanel({ agentId }: { agentId: string }) {
  const { data: variables = [], isLoading } = useAgentProfileVariables(agentId);
  const createMutation = useCreateAgentProfileVariable(agentId);
  const updateMutation = useUpdateAgentProfileVariable(agentId);
  const deleteMutation = useDeleteAgentProfileVariable(agentId);

  useFlushRetryOnMount(agentId);

  const rows = useMemo<PanelRow[]>(
    () =>
      variables.map((v) => ({
        id: v.id,
        key: v.key,
        value: v.value,
        description: v.description,
      })),
    [variables],
  );

  const onCreate = useCallback(
    async (input: ProfileVarFormValues) => {
      await createMutation.mutateAsync({
        key: input.key,
        value: input.value,
        description: input.description?.trim() || null,
      });
    },
    [createMutation],
  );
  const onUpdate = useCallback(
    async (id: string, patch: ProfileVarFormValues) => {
      await updateMutation.mutateAsync({
        variableId: id,
        patch: {
          key: patch.key,
          value: patch.value,
          // Empty string (user cleared the field) is intentional — the backend
          // normalises whitespace-only / empty to NULL. Sending `null` would be
          // treated as "leave unchanged" by the PATCH-style update route.
          description: patch.description?.trim() ?? '',
        },
      });
    },
    [updateMutation],
  );
  const onDelete = useCallback(
    async (id: string) => {
      await deleteMutation.mutateAsync(id);
    },
    [deleteMutation],
  );

  return (
    <VariablesPanel
      rows={rows}
      loading={isLoading}
      mutating={createMutation.isPending || updateMutation.isPending || deleteMutation.isPending}
      onCreate={onCreate}
      onUpdate={onUpdate}
      onDelete={onDelete}
      existingKeys={rows.map((r) => r.key)}
    />
  );
}

// ── CREATE mode (RHF drafts) ────────────────────────────────────────────

function CreateModePanel() {
  const { control, setValue, getValues } = useFormContext<AgentFormState>();
  const drafts =
    (useWatch({ control, name: 'profile_variable_drafts' }) as ProfileVariableDraft[]) ?? [];

  const rows = useMemo<PanelRow[]>(
    () =>
      drafts.map((d) => ({
        id: d._draftId,
        key: d.key,
        value: d.value,
        description: d.description,
      })),
    [drafts],
  );

  const replaceDrafts = useCallback(
    (next: ProfileVariableDraft[]) => {
      setValue('profile_variable_drafts', next, { shouldDirty: true });
    },
    [setValue],
  );

  const onCreate = useCallback(
    async (input: ProfileVarFormValues) => {
      const current = getValues('profile_variable_drafts') ?? [];
      replaceDrafts([
        ...current,
        {
          _draftId: newDraftId(),
          key: input.key,
          value: input.value,
          description: input.description?.trim() || null,
        },
      ]);
    },
    [getValues, replaceDrafts],
  );
  const onUpdate = useCallback(
    async (id: string, patch: ProfileVarFormValues) => {
      const current = getValues('profile_variable_drafts') ?? [];
      replaceDrafts(
        current.map((d) =>
          d._draftId === id
            ? {
                _draftId: d._draftId,
                key: patch.key,
                value: patch.value,
                // Empty string (user cleared the field) is intentional — the backend
                // normalises whitespace-only / empty to NULL. Sending `null` would be
                // treated as "leave unchanged" by the PATCH-style update route.
                description: patch.description?.trim() ?? '',
              }
            : d,
        ),
      );
    },
    [getValues, replaceDrafts],
  );
  const onDelete = useCallback(
    async (id: string) => {
      const current = getValues('profile_variable_drafts') ?? [];
      replaceDrafts(current.filter((d) => d._draftId !== id));
    },
    [getValues, replaceDrafts],
  );

  return (
    <VariablesPanel
      rows={rows}
      loading={false}
      mutating={false}
      onCreate={onCreate}
      onUpdate={onUpdate}
      onDelete={onDelete}
      existingKeys={rows.map((r) => r.key)}
      hint="These variables will be created together with the agent when you save."
    />
  );
}

function newDraftId(): string {
  return `draft-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Read the sessionStorage handoff from `AgentEditorShell.flushProfileVariableDrafts`
 * and silently retry each still-failed draft against the just-created agent.
 * A successful retry disappears with just a toast; anything that STILL fails
 * shows the raw draft data via toast + console so the user can hand-copy the
 * value into the Add modal without losing it. Runs once per mount + agentId. */
function useFlushRetryOnMount(agentId: string) {
  const ranForRef = useRef<string | null>(null);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (ranForRef.current === agentId) return;
    ranForRef.current = agentId;

    const key = PROFILE_VAR_FLUSH_FAILED_KEY(agentId);
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return;
    window.sessionStorage.removeItem(key);

    let drafts: ProfileVariableDraft[] = [];
    try {
      const parsed = JSON.parse(raw) as { drafts?: unknown };
      if (Array.isArray(parsed?.drafts)) drafts = parsed.drafts as ProfileVariableDraft[];
    } catch (err) {
      console.warn('[profile-variables] could not parse stashed failed drafts', err);
      return;
    }
    if (!drafts.length) return;

    (async () => {
      const stillFailed: ProfileVariableDraft[] = [];
      for (const draft of drafts) {
        try {
          await createAgentProfileVariable(agentId, {
            key: draft.key,
            value: draft.value,
            description: draft.description ?? undefined,
          });
        } catch (err) {
          console.error(
            `[profile-variables] retry failed for stashed draft key="${draft.key}"`,
            err,
            draft,
          );
          stillFailed.push(draft);
        }
      }
      if (stillFailed.length === 0) {
        showToast.success(`Recovered ${drafts.length} profile variable(s) from the previous save.`);
      } else {
        showToast.error(
          `${stillFailed.length} of ${drafts.length} pending profile variable(s) still failed — check the browser console for the values and re-add them manually.`,
        );
      }
    })();
  }, [agentId]);
}

// ── Shared panel ────────────────────────────────────────────────────────

interface VariablesPanelProps {
  rows: PanelRow[];
  loading: boolean;
  mutating: boolean;
  onCreate: (input: ProfileVarFormValues) => Promise<void>;
  onUpdate: (id: string, patch: ProfileVarFormValues) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  /** Existing keys currently on this agent — used to reject duplicates client-side. */
  existingKeys: string[];
  /** Optional inline hint above the table. */
  hint?: string;
}

function VariablesPanel({
  rows,
  loading,
  mutating,
  onCreate,
  onUpdate,
  onDelete,
  existingKeys,
  hint,
}: VariablesPanelProps) {
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<PanelRow | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<PanelRow | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const closeAddOrEdit = () => {
    if (submitting || mutating) return;
    setAddOpen(false);
    setEditTarget(null);
  };

  const submit = async (values: ProfileVarFormValues) => {
    // Client-side dup check — mirrors the backend `UNIQUE(agent_id, key)`. In
    // create mode there's no server call to catch this; in edit mode the
    // server also enforces it but the local check gives an instant error.
    const clash = existingKeys
      .filter((k) => (editTarget ? k !== editTarget.key : true))
      .some((k) => k === values.key);
    if (clash) {
      showToast.error(`A profile variable named "${values.key}" already exists on this agent.`);
      return;
    }

    setSubmitting(true);
    try {
      if (editTarget) {
        await onUpdate(editTarget.id, values);
        showToast.success('Profile variable updated.');
      } else {
        await onCreate(values);
        showToast.success('Profile variable added.');
      }
      setAddOpen(false);
      setEditTarget(null);
    } catch (err) {
      handleApiError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setSubmitting(true);
    try {
      await onDelete(deleteTarget.id);
      showToast.success('Profile variable deleted.');
      setDeleteTarget(null);
    } catch (err) {
      handleApiError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = useMemo<CustomTableColumn<PanelRow>[]>(
    () => [
      {
        key: 'key',
        title: 'Key',
        dataIndex: 'key',
        render: (_v, row) => <span className="font-mono text-xs">{`{{profile.${row.key}}}`}</span>,
      },
      {
        key: 'value',
        title: 'Value',
        dataIndex: 'value',
        render: (_v, row) => {
          const val = row.value ?? '';
          if (!val) return <span className="italic text-muted-foreground">empty</span>;
          // Only wrap in a tooltip when the value is actually truncated —
          // rendering `CustomTooltip` for every row would otherwise pop up an
          // empty bubble on hover for short values.
          if (val.length <= 80) {
            return <span className="line-clamp-1 break-all text-sm">{val}</span>;
          }
          return (
            <CustomTooltip content={val}>
              <span className="line-clamp-1 break-all text-sm">{`${val.slice(0, 79)}…`}</span>
            </CustomTooltip>
          );
        },
      },
      {
        key: 'description',
        title: 'Description',
        dataIndex: 'description',
        render: (_v, row) =>
          row.description ? (
            <span className="text-sm text-muted-foreground">{row.description}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: '96px',
        render: (_v, row) => (
          <div className="flex items-center justify-end gap-1">
            <CustomButton
              type="text"
              size="icon-sm"
              aria-label={`Edit ${row.key}`}
              onClick={() => setEditTarget(row)}
              icon={<Pencil className="size-4 text-muted-foreground" />}
            />
            <CustomButton
              type="text"
              size="icon-sm"
              aria-label={`Delete ${row.key}`}
              onClick={() => setDeleteTarget(row)}
              icon={<Trash2 className="size-4 text-muted-foreground" />}
            />
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-col gap-3">
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      <div className="flex justify-end">
        <CustomButton
          type="primary"
          size="sm"
          onClick={() => setAddOpen(true)}
          icon={<Plus className="size-3.5" />}
        >
          Add variable
        </CustomButton>
      </div>
      <CustomTable<PanelRow>
        columns={columns}
        dataSource={rows}
        rowKey="id"
        loading={loading}
        pagination={false}
        searchable
        searchPlaceholder="Search variables…"
        emptyState={
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
            <span className="text-sm text-muted-foreground">No profile variables yet.</span>
            <span className="text-xs text-muted-foreground">
              Add one to reference it as <span className="font-mono">{'{{profile.<key>}}'}</span> in
              prompts and workflows.
            </span>
          </div>
        }
      />

      <ProfileVariableModal
        open={addOpen || !!editTarget}
        onClose={closeAddOrEdit}
        initial={
          editTarget
            ? {
                id: editTarget.id,
                organization_id: '',
                agent_id: '',
                key: editTarget.key,
                value: editTarget.value,
                description: editTarget.description,
                created_at: null,
                updated_at: null,
              }
            : null
        }
        onSubmit={submit}
        submitting={submitting || mutating}
      />

      <CustomModal
        open={!!deleteTarget}
        onClose={() => (submitting || mutating ? undefined : setDeleteTarget(null))}
        title="Delete profile variable?"
        description={
          deleteTarget
            ? `Any {{profile.${deleteTarget.key}}} reference in this agent's prompt or workflow will render literally after deletion.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={submitting || mutating}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
