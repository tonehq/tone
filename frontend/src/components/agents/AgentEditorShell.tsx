'use client';

import { useAtom } from 'jotai';
import { ArrowLeft, Eye, Loader2, Phone, Save, Sparkles, Trash2 } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';

import {
  createAgentAtom,
  deleteAgentAtom,
  fetchAgentAtom,
  updateAgentAtom,
} from '@/atoms/AgentsAtom';
import { AgentEditorProvider } from '@/components/agents/AgentEditorContext';
import { AgentFormNavProvider } from '@/components/agents/agent-form/AgentFormNav';
import { AGENT_SECTION_KEYS, buildAgentNav } from '@/components/agents/agent-form/sectionNav';
import ReviewStep from '@/components/agents/agent-form/steps/ReviewStep';
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
  formStateToUpdatePayload,
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

  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [originalState, setOriginalState] = useState<AgentFormState | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);

  const methods = useForm<AgentFormState>({
    defaultValues: defaultFormState(agentType),
    mode: 'onChange',
  });

  const basePath = isEditMode
    ? `/agents/edit/${agentType}/${agentId}`
    : `/agents/create/${agentType}`;

  const isDirty = methods.formState.isDirty;
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

  // ─── load on edit ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isEditMode || !agentId) return;
    let cancelled = false;
    setLoading(true);
    fetchAgent(agentId)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
        const hydrated = agentDetailToFormState(d);
        methods.reset(hydrated);
        setOriginalState(hydrated);
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
  }, [agentId, fetchAgent, isEditMode, methods, router]);

  // ─── save / delete / activate ───────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    const valid = await methods.trigger();
    if (!valid) {
      router.push(`${basePath}/basics`);
      return;
    }
    const values = methods.getValues();
    setSaving(true);
    try {
      if (isEditMode && agentId && originalState) {
        const diff = formStateToUpdatePayload(values, originalState);
        if (Object.keys(diff).length === 0) {
          showToast.success('No changes', 'Nothing to update.');
          setSaving(false);
          return;
        }
        const updated = await updateAgent({ id: agentId, values: diff });
        setDetail(updated);
        const fresh = agentDetailToFormState(updated);
        methods.reset(fresh);
        setOriginalState(fresh);
        showToast.success('Agent updated');
      } else {
        const created = await createAgent(formStateToCreatePayload(values));
        showToast.success('Agent created');
        methods.reset(values);
        router.push(`/agents/edit/${created.agent_type}/${created.id}/overview`);
      }
    } catch (err) {
      const detailErr = (err as any)?.response?.data?.detail;
      if (typeof detailErr === 'object' && detailErr?.errors) {
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
      } else {
        handleApiError(err);
      }
    } finally {
      setSaving(false);
    }
  }, [agentId, basePath, createAgent, isEditMode, methods, originalState, router, updateAgent]);

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
        // Keep the form in sync without marking it dirty.
        methods.setValue('is_active', active, { shouldDirty: false });
        setOriginalState((prev) => (prev ? { ...prev, is_active: active } : prev));
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

  const handleReviewJump = useCallback(
    (stepIndex: number) => {
      const key = AGENT_SECTION_KEYS[stepIndex];
      if (!key) return;
      setPreviewOpen(false);
      router.push(`${basePath}/${key}`);
    },
    [basePath, router],
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
                  <CustomButton
                    type="default"
                    size="sm"
                    icon={<Eye className="size-4" />}
                    onClick={() => setPreviewOpen(true)}
                    className="h-8"
                  >
                    Preview
                  </CustomButton>
                  <CustomButton
                    type="primary"
                    size="sm"
                    icon={
                      saving ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Save className="size-3.5" />
                      )
                    }
                    onClick={handleSave}
                    loading={saving}
                    className="h-8"
                  >
                    {isEditMode ? 'Save changes' : 'Create agent'}
                  </CustomButton>
                </div>
              </header>

              {/* Body — the routed section */}
              <main className="min-h-0 flex-1 overflow-auto px-5 py-5 lg:px-8 lg:py-6">
                {loading ? (
                  <AppLoader className="h-full" />
                ) : (
                  <div className="mx-auto max-w-3xl">{children}</div>
                )}
              </main>
            </div>

            <CustomModal
              open={previewOpen}
              onClose={() => setPreviewOpen(false)}
              title="Agent preview"
              description="Read-only sanity check of the current configuration."
              hideFooter
              width="sm:max-w-3xl"
              className="max-h-[85vh] overflow-hidden"
              contentClassName="max-h-[calc(85vh-90px)] overflow-y-auto"
            >
              <ReviewStep onJump={handleReviewJump} />
            </CustomModal>

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
