'use client';

import { useAtom } from 'jotai';
import { isEqual } from 'lodash';
import { ArrowLeft, Phone, Sparkles, Trash2 } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';

import {
  createAgentAtom,
  deleteAgentAtom,
  deleteAgentVersionAtom,
  fetchAgentAtom,
  saveAgentAsNewVersionAtom,
  switchActiveAgentVersionAtom,
  updateAgentAtom,
} from '@/atoms/AgentsAtom';
import { AgentEditorProvider } from '@/components/agents/AgentEditorContext';
import AgentSaveActions, { type AgentSaveAction } from '@/components/agents/AgentSaveActions';
import AgentVersionSelector from '@/components/agents/AgentVersionSelector';
import PublishVersionConfirmModal from '@/components/agents/PublishVersionConfirmModal';
import { AgentFormNavProvider } from '@/components/agents/agent-form/AgentFormNav';
import { buildAgentNav } from '@/components/agents/agent-form/sectionNav';
import { AccountMenu } from '@/components/layout/AccountMenu';
import { isSidebarItemActive, SidebarShell } from '@/components/layout/SidebarShell';
import { AppLoader, CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { useNavigation } from '@/contexts/navigation';
import { useUnsavedChangesGuard } from '@/hooks/useUnsavedChangesGuard';
import type { AgentDetail, AgentDirection, AgentFormState } from '@/types/agent';
import {
  agentDetailToFormState,
  defaultFormState,
  formStateToCreatePayload,
} from '@/utils/agentFormUtils';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface AgentEditorShellProps {
  agentType: AgentDirection;
  agentId?: string;
  children: React.ReactNode;
}

const DIRECTION_STYLES: Record<AgentDirection, string> = {
  inbound:
    'bg-emerald-500/15 text-emerald-700 ring-1 ring-inset ring-emerald-500/20 dark:bg-emerald-500/25 dark:text-emerald-200 dark:ring-emerald-400/40',
  outbound:
    'bg-violet-500/15 text-violet-700 ring-1 ring-inset ring-violet-500/20 dark:bg-violet-500/25 dark:text-violet-200 dark:ring-violet-400/40',
  both: 'bg-sky-500/15 text-sky-700 ring-1 ring-inset ring-sky-500/20 dark:bg-sky-500/25 dark:text-sky-200 dark:ring-sky-400/40',
};

const HEADER_TINT: Record<AgentDirection, string> = {
  inbound:
    'bg-gradient-to-r from-emerald-500/5 via-transparent to-transparent dark:from-emerald-500/10',
  outbound:
    'bg-gradient-to-r from-violet-500/5 via-transparent to-transparent dark:from-violet-500/10',
  both: 'bg-gradient-to-r from-sky-500/5 via-transparent to-transparent dark:from-sky-500/10',
};

export default function AgentEditorShell({ agentType, agentId, children }: AgentEditorShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const isEditMode = !!agentId;
  const mode = isEditMode ? 'edit' : 'create';

  const [, fetchAgent] = useAtom(fetchAgentAtom);
  const [, createAgent] = useAtom(createAgentAtom);
  const [, updateAgent] = useAtom(updateAgentAtom);
  const [, deleteAgent] = useAtom(deleteAgentAtom);
  const [, saveAgentAsNewVersion] = useAtom(saveAgentAsNewVersionAtom);
  const [, switchActiveAgentVersion] = useAtom(switchActiveAgentVersionAtom);
  const [, deleteAgentVersion] = useAtom(deleteAgentVersionAtom);

  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  /** Which version is loaded in the form. Null until the agent has loaded. */
  const [viewedConfigId, setViewedConfigId] = useState<string | null>(null);

  const methods = useForm<AgentFormState>({
    defaultValues: defaultFormState(agentType),
    mode: 'onChange',
  });

  const basePath = isEditMode
    ? `/agents/edit/${agentType}/${agentId}`
    : `/agents/create/${agentType}`;

  // The form's "saved" snapshot. Used as the source of truth for dirty
  // detection (deep-compared against current values) because RHF's own
  // `formState.isDirty` can spuriously flip on load — child components like
  // the TipTap prompt editor re-sync internal state via a useEffect and can
  // round-trip the loaded text through ProseMirror's schema, leaving RHF's
  // deep-equality off by a whitespace-level diff even when the user has not
  // typed anything. Comparing against the loaded snapshot sidesteps that.
  const loadedBaselineRef = useRef<AgentFormState>(defaultFormState(agentType));

  const watchedValues = useWatch({ control: methods.control });

  const isDirty = useMemo(
    () => !isEqual(methods.getValues(), loadedBaselineRef.current),
    [watchedValues, methods],
  );
  const { promptOpen, guardedAction, confirmLeave, cancelLeave } = useUnsavedChangesGuard(isDirty, {
    // Switching sections stays under the editor base path and keeps the same
    // persisted form — so it should never trigger the unsaved-changes prompt.
    // Only navigating OUT of the editor warns.
    isInternalNavigation: (dest) => dest.startsWith(basePath),
  });

  const safeNavigate = useCallback(
    (href: string) => guardedAction(() => router.push(href)),
    [guardedAction, router],
  );
  const navContextValue = useMemo(() => ({ safeNavigate }), [safeNavigate]);
  const navGroups = useMemo(() => buildAgentNav(basePath, mode), [basePath, mode]);
  const flatItems = useMemo(() => navGroups.flatMap((g) => g.items), [navGroups]);

  /** Push a freshly-loaded AgentDetail into local state + the RHF form.
   *
   * Does NOT touch `viewedConfigId` — that's the user's explicit chip
   * selection and only moves when the user picks a different version from the
   * dropdown (or on initial load). Save creates a draft and updates the form,
   * but the chip should stay where the user put it (typically the published
   * version) — otherwise the chip would jump to the draft right after Save,
   * and the user would see Publish enable for a version they didn't choose.
   *
   * Dirty-state hygiene: the synchronous `reset` clears `isDirty`, but some
   * child components (notably the TipTap-backed prompt editor) sync their
   * internal state via a `useEffect` on the form value and can re-fire
   * `field.onChange` with a normalised string that differs subtly from the
   * loaded value — which flips RHF's deep-equality back to dirty. A second
   * reset deferred past React's effect cycle re-baselines after those
   * children settle, so the unsaved-changes guard doesn't fire spuriously on
   * the very next click (e.g. opening the version dropdown after Save).
   */
  const applyDetail = useCallback(
    (d: AgentDetail) => {
      setDetail(d);
      const formState = agentDetailToFormState(d);
      loadedBaselineRef.current = formState;
      methods.reset(formState);
      setTimeout(() => methods.reset(methods.getValues()), 0);
    },
    [methods],
  );

  // ─── load on edit ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isEditMode || !agentId) return;
    let cancelled = false;
    setLoading(true);
    fetchAgent(agentId)
      .then((d) => {
        if (cancelled) return;
        applyDetail(d);
        // Initial chip selection = whatever the backend resolved as current
        // (the published version when no config_id is requested).
        setViewedConfigId(d.config?.id ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        if ((err as { response?: { status?: number } })?.response?.status === 404) {
          showToast.error('Agent not found', 'It may have been deleted.');
          router.replace('/agents');
          return;
        }
        handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, applyDetail, fetchAgent, isEditMode, router]);

  /** Map a server validation-error payload onto RHF fields and jump to the
   * tab where the first failure lives. */
  const applyServerValidation = useCallback(
    (err: unknown): boolean => {
      const detailErr = (err as any)?.response?.data?.detail;
      if (!detailErr || typeof detailErr !== 'object' || !detailErr.errors) return false;
      const validationErrors = detailErr.errors as Record<string, Record<string, string[]>>;
      let navigated = false;
      for (const [settingsKey, fields] of Object.entries(validationErrors)) {
        for (const [fieldName, messages] of Object.entries(fields)) {
          const path = `config.${settingsKey}.${fieldName}` as any;
          methods.setError(path, { type: 'server', message: messages[0] });
        }
        if (!navigated) {
          if (settingsKey === 'llm_settings') router.push(`${basePath}/ai`);
          else if (settingsKey === 'voice_settings' || settingsKey === 'stt_settings')
            router.push(`${basePath}/voice`);
          navigated = true;
        }
      }
      showToast.error(
        'Validation failed',
        detailErr.message || 'Please fix the highlighted fields.',
      );
      return true;
    },
    [basePath, methods, router],
  );

  // ─── save / delete / publish ────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    const valid = await methods.trigger();
    if (!valid) {
      router.push(`${basePath}/basics`);
      return;
    }
    // In edit mode, no edits → no new draft. Without this guard, spam-clicking
    // Save would pile up identical empty drafts in the version history. The
    // create flow always proceeds because the agent itself doesn't exist yet.
    if (isEditMode && agentId && isEqual(methods.getValues(), loadedBaselineRef.current)) {
      showToast.success('No changes', 'Nothing to save.');
      return;
    }
    const values = methods.getValues();
    setSaving(true);
    try {
      // Create flow — first save creates the agent (which is born already published).
      if (!isEditMode || !agentId) {
        const created = await createAgent(formStateToCreatePayload(values));
        showToast.success('Agent created');
        methods.reset(values);
        router.push(`/agents/edit/${created.agent_type}/${created.id}/overview`);
        return;
      }

      // Edit flow — every Save creates a fresh draft version. The published
      // version that's serving calls is not touched until the user clicks
      // Publish. We send the full form state (not a diff) so the new draft
      // reflects exactly what the user sees — see backend
      // `_create_new_version_config` for how the snapshot is built. We also
      // declare `source_config_id` so the backend clones tools / MCP / KB
      // from the version the user was previewing rather than the published
      // one.
      const full = formStateToCreatePayload(values);
      const updated = await saveAgentAsNewVersion({
        agentId,
        values: {
          config: full.config,
          tool_ids: full.tool_ids,
          mcp_server_ids: full.mcp_server_ids,
          upload_ids: full.upload_ids,
          phone_numbers: full.phone_numbers,
          source_config_id: detail?.config?.id ?? null,
        },
      });
      applyDetail(updated);
      showToast.success(
        'Draft saved',
        updated.config?.version != null
          ? `v${updated.config.version} was saved as a new draft. Select it in the version dropdown to publish.`
          : undefined,
      );
    } catch (err) {
      if (!applyServerValidation(err)) handleApiError(err);
    } finally {
      setSaving(false);
    }
  }, [
    agentId,
    applyDetail,
    applyServerValidation,
    basePath,
    createAgent,
    detail,
    isEditMode,
    methods,
    router,
    saveAgentAsNewVersion,
  ]);

  const handleViewVersion = useCallback(
    async (configId: string) => {
      // Compare against what's actually loaded in the form — NOT viewedConfigId
      // (the chip). After Save, the chip stays pinned to the published version
      // while the form shows the new draft; clicking the published row in the
      // dropdown must still reload it into the form, so we key the no-op
      // check off `detail.config.id`.
      if (!agentId || configId === detail?.config?.id) return;
      setLoading(true);
      try {
        const d = await fetchAgent({ agentId, configId });
        applyDetail(d);
        // Explicit user pick — chip + form both move to this version.
        setViewedConfigId(configId);
      } catch (err) {
        handleApiError(err);
      } finally {
        setLoading(false);
      }
    },
    [agentId, applyDetail, detail?.config?.id, fetchAgent],
  );

  const handlePublish = useCallback(
    async (configId: string) => {
      if (!agentId || !configId) return;
      setPublishing(true);
      try {
        const updated = await switchActiveAgentVersion({ agentId, configId });
        applyDetail(updated);
        // Chip follows the published version once promotion succeeds — so the
        // user lands on the version they just made live.
        setViewedConfigId(updated.config?.id ?? configId);
        const v = updated.versions?.find((row) => row.id === configId)?.version;
        showToast.success(
          'Version published',
          v != null ? `v${v} is now serving calls.` : undefined,
        );
        setPublishOpen(false);
      } catch (err) {
        // Leave the modal open on error — the user can immediately retry or
        // cancel without losing the dialog context.
        handleApiError(err);
      } finally {
        setPublishing(false);
      }
    },
    [agentId, applyDetail, switchActiveAgentVersion],
  );

  const handleDeleteVersion = useCallback(
    async (configId: string) => {
      if (!agentId) return;
      try {
        await deleteAgentVersion({ agentId, configId });
        showToast.success('Version deleted');
        const refreshed = await fetchAgent(agentId);
        applyDetail(refreshed);
        // If the chip was pointing at the row we just deleted, fall back to
        // whatever the backend now resolves as current (the published one).
        if (configId === viewedConfigId) {
          setViewedConfigId(refreshed.config?.id ?? null);
        }
      } catch (err) {
        handleApiError(err);
      }
    },
    [agentId, applyDetail, deleteAgentVersion, fetchAgent, viewedConfigId],
  );

  const handleConfirmDelete = useCallback(async () => {
    if (!agentId) return;
    setDeleting(true);
    try {
      await deleteAgent(agentId);
      methods.reset(methods.getValues());
      router.push('/agents');
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  }, [agentId, deleteAgent, methods, router]);

  const setActive = useCallback(
    async (active: boolean) => {
      if (!agentId) return;
      try {
        const updated = await updateAgent({ id: agentId, values: { is_active: active } });
        setDetail(updated);
        // Reset (not setValue with shouldDirty:false) so _formValues AND
        // _defaultValues update together. A bare setValue would leave the
        // defaults stale, and any later RHF dirty recompute would flip
        // isDirty true even though the user changed nothing — surfacing
        // as a spurious "discard changes?" prompt on the next navigation
        // or version pick.
        const nextValues = { ...methods.getValues(), is_active: active };
        loadedBaselineRef.current = { ...loadedBaselineRef.current, is_active: active };
        methods.reset(nextValues);
        showToast.success(active ? 'Agent activated' : 'Agent deactivated');
      } catch (err) {
        handleApiError(err);
      }
    },
    [agentId, methods, updateAgent],
  );

  const editorContextValue = useMemo(
    () => ({ detail, agentId: agentId ?? null, agentType, setActive }),
    [detail, agentId, agentType, setActive],
  );

  // ─── derived ──────────────────────────────────────────────────────────────
  const agentName = methods.watch('name') || (isEditMode ? 'Untitled agent' : 'New agent');
  const agentInitial = (agentName.trim().charAt(0) || 'A').toUpperCase();

  const versions = detail?.versions ?? [];
  const publishedVersion = useMemo(() => versions.find((v) => v.is_live) ?? null, [versions]);
  /** What the form is rendering right now. Driven by the backend response
   *  (`detail.config`) — Save returns the new draft here, which is how the
   *  user keeps seeing their edits even though the chip stays put. */
  const loadedVersion = useMemo(
    () => versions.find((v) => v.id === detail?.config?.id) ?? null,
    [versions, detail?.config?.id],
  );
  /** Publish opens its own version picker; the toolbar button is enabled as
   *  long as there's at least one non-published version available to pick. */
  const canPublish = useMemo(
    () =>
      publishedVersion === null
        ? versions.length > 0
        : versions.some((v) => v.id !== publishedVersion.id),
    [versions, publishedVersion],
  );
  /** True when the form is showing a draft (something other than the
   *  published version). Triggers the amber banner. */
  const formHasDraft =
    publishedVersion !== null && loadedVersion !== null && loadedVersion.id !== publishedVersion.id;

  // Switching the viewed version overwrites the form with fetched data — wrap
  // in guardedAction so unsaved edits get the same "Discard changes?" prompt
  // as other navigations.
  const safeViewVersion = useCallback(
    (configId: string) => guardedAction(() => void handleViewVersion(configId)),
    [guardedAction, handleViewVersion],
  );

  const dispatchAction = useCallback(
    (action: AgentSaveAction) => {
      if (action === 'publish') {
        // Publish reloads the response into the form — any unsaved edits would
        // be silently discarded. Route through guardedAction so the user gets
        // the standard "Discard changes?" prompt first.
        guardedAction(() => setPublishOpen(true));
        return;
      }
      void handleSave();
    },
    [guardedAction, handleSave],
  );

  return (
    <FormProvider {...methods}>
      <AgentFormNavProvider value={navContextValue}>
        <AgentEditorProvider value={editorContextValue}>
          <div className="flex h-full w-full min-w-0 bg-background">
            {/* ── Editor rail (desktop) — shares SidebarShell with the app sidebar ── */}
            <SidebarShell
              groups={navGroups}
              collapsed={sidebarCollapsed}
              onToggle={toggleSidebar}
              activeLayoutId="agent-editor"
              className="hidden lg:flex"
              primary={(collapsed) => (
                <BackToAgents collapsed={collapsed} onLeave={guardedAction} />
              )}
              footer={(collapsed) => <AccountMenu collapsed={collapsed} />}
            />

            {/* ── Content column ─────────────────────────────────────────── */}
            <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
              {/* Mobile top bar */}
              <div className="flex shrink-0 flex-col gap-2 border-b border-border/60 bg-sidebar/60 px-4 pb-2 pt-2.5 backdrop-blur lg:hidden">
                <div className="flex items-center gap-3">
                  <CustomButton
                    type="text"
                    aria-label="Back to agents"
                    icon={<ArrowLeft className="size-4" />}
                    onClick={() => guardedAction(() => router.push('/agents'))}
                    className="size-8 rounded-lg p-0 text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                  />
                  <span className="text-[15px] font-semibold tracking-tight">Agent editor</span>
                </div>
                <nav
                  aria-label="Agent sections (mobile)"
                  className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pb-0.5"
                >
                  {flatItems.map((item) => {
                    const Icon = item.icon;
                    const active = isSidebarItemActive(pathname, item);
                    return (
                      <CustomButton
                        key={item.href}
                        type="text"
                        size="sm"
                        onClick={() => router.push(item.href)}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'shrink-0 gap-1.5 rounded-full px-3 text-[12px]',
                          active
                            ? 'bg-sidebar-accent text-foreground'
                            : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                        )}
                      >
                        <Icon className="size-3.5" />
                        {item.label}
                      </CustomButton>
                    );
                  })}
                </nav>
              </div>

              {/* Save-bar header */}
              <header
                className={cn(
                  'relative flex shrink-0 items-center gap-3 overflow-hidden border-b border-border/60 px-5 py-3',
                  HEADER_TINT[agentType],
                )}
              >
                <div
                  className={cn(
                    'flex size-10 shrink-0 items-center justify-center rounded-xl text-base font-semibold shadow-sm',
                    DIRECTION_STYLES[agentType],
                  )}
                  aria-hidden
                >
                  {agentInitial}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
                      {agentName}
                    </h1>
                    <Badge
                      className={cn(
                        'inline-flex shrink-0 items-center gap-1 px-1.5 py-0 text-[10px] capitalize',
                        DIRECTION_STYLES[agentType],
                      )}
                    >
                      <Phone className="size-2.5" />
                      {agentType}
                    </Badge>
                    {!isEditMode && (
                      <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground">
                        <Sparkles className="size-3" />
                        New
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                    {isEditMode ? 'Editing agent configuration' : 'Set up a new voice agent'}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {isEditMode && versions.length > 0 && (
                    <AgentVersionSelector
                      versions={versions}
                      selectedConfigId={viewedConfigId}
                      onSelect={safeViewVersion}
                      onDelete={handleDeleteVersion}
                      disabled={loading || saving || publishing}
                    />
                  )}
                  {isEditMode && (
                    <CustomButton
                      type="text"
                      size="sm"
                      icon={<Trash2 className="size-4" />}
                      onClick={() => setDeleteOpen(true)}
                      className="h-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    >
                      Delete
                    </CustomButton>
                  )}
                  <AgentSaveActions
                    mode={isEditMode ? 'edit' : 'create'}
                    canPublish={canPublish}
                    saving={saving}
                    publishing={publishing}
                    onAction={dispatchAction}
                  />
                </div>
              </header>

              {/* Draft banner: drives off the form-loaded version, not the chip.
                  The chip stays pinned to the published version after Save, so
                  without this we'd hide the banner exactly when the user most
                  needs to know they're looking at unpublished edits. */}
              {isEditMode && formHasDraft && loadedVersion && publishedVersion && (
                <div className="shrink-0 border-b border-amber-500/30 bg-amber-500/10 px-5 py-2 text-[12px] text-amber-900 dark:text-amber-200">
                  Viewing v{loadedVersion.version} (draft). v{publishedVersion.version} is the
                  published version serving calls — click Publish to promote v
                  {loadedVersion.version}.
                </div>
              )}

              {/* Body — the routed section */}
              <main className="min-h-0 flex-1 overflow-auto px-5 py-5 lg:px-8 lg:py-6">
                {loading ? (
                  <AppLoader className="h-full" />
                ) : (
                  <div className="mx-auto h-full max-w-3xl">{children}</div>
                )}
              </main>
            </div>

            <CustomModal
              open={deleteOpen}
              onClose={() => setDeleteOpen(false)}
              title="Delete agent"
              description="This removes the agent and its configuration. Tools, MCP servers and uploads stay intact."
              confirmText="Delete"
              confirmType="danger"
              confirmLoading={deleting}
              onConfirm={handleConfirmDelete}
            />

            <CustomModal
              open={promptOpen}
              onClose={cancelLeave}
              title="Discard unsaved changes?"
              description="You have unsaved changes on this agent. If you leave now, those changes will be lost."
              confirmText="Discard"
              confirmType="danger"
              cancelText="Keep editing"
              onConfirm={confirmLeave}
            />

            <PublishVersionConfirmModal
              open={publishOpen}
              // Ignore close requests while the publish call is in flight —
              // ESC / overlay-click would otherwise abandon the dialog while
              // the version pointer is mid-flip.
              onClose={() => {
                if (!publishing) setPublishOpen(false);
              }}
              onConfirm={handlePublish}
              versions={versions}
              publishedVersionId={publishedVersion?.id ?? null}
              loading={publishing}
            />
          </div>
        </AgentEditorProvider>
      </AgentFormNavProvider>
    </FormProvider>
  );
}

/** Primary rail slot — guarded return to the agents list. */
function BackToAgents({
  collapsed,
  onLeave,
}: {
  collapsed: boolean;
  onLeave: (action: () => void) => void;
}) {
  const router = useRouter();
  const go = () => onLeave(() => router.push('/agents'));

  if (collapsed) {
    return (
      <CustomButton
        type="text"
        aria-label="Back to agents"
        onClick={go}
        className="mx-auto flex size-8 items-center justify-center rounded-lg bg-primary/10 p-0 ring-1 ring-inset ring-primary/10 hover:bg-primary/15"
      >
        <ArrowLeft className="h-4 w-4 text-primary" strokeWidth={1.75} />
      </CustomButton>
    );
  }

  return (
    <CustomButton
      type="text"
      fullWidth
      onClick={go}
      className="h-auto justify-start gap-3 rounded-lg px-2 py-2 text-left font-normal hover:bg-sidebar-accent/60"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-inset ring-primary/10">
        <ArrowLeft className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-semibold leading-tight tracking-tight">
          Agents
        </span>
        <span className="block truncate text-[11.5px] leading-tight text-muted-foreground">
          Back to agents
        </span>
      </span>
    </CustomButton>
  );
}
