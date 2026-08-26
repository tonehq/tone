'use client';

import { useAtom } from 'jotai';
import { isEqual } from 'lodash';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';

import {
  createAgentAtom,
  createAgentVersionAtom,
  deleteAgentAtom,
  deleteAgentVersionAtom,
  fetchAgentAtom,
  switchActiveAgentVersionAtom,
  updateAgentAtom,
  updateAgentVersionAtom,
} from '@/atoms/AgentsAtom';
import { fetchAgentReadinessAtom, fetchAgentReadinessSummaryAtom } from '@/atoms/ReadinessAtom';
import { AgentEditorProvider } from '@/components/agents/AgentEditorContext';
import AgentSaveActions, { type AgentSaveAction } from '@/components/agents/AgentSaveActions';
import { AgentTypeBadge, DIRECTION_TONES } from '@/components/agents/AgentTypeBadge';
import AgentVersionSelector from '@/components/agents/AgentVersionSelector';
import CreateVersionModal, {
  type CreateVersionSelection,
} from '@/components/agents/CreateVersionModal';
import PublishVersionConfirmModal from '@/components/agents/PublishVersionConfirmModal';
import ReadinessBadge from '@/components/agents/readiness/ReadinessBadge';
import ReadinessConfirmDialog from '@/components/agents/readiness/ReadinessConfirmDialog';
import ReadinessDrawer from '@/components/agents/readiness/ReadinessDrawer';
import SaveAsTemplateModal from '@/components/agents/SaveAsTemplateModal';
import { AgentFormNavProvider } from '@/components/agents/agent-form/AgentFormNav';
import { buildAgentNav } from '@/components/agents/agent-form/sectionNav';
import { AccountMenu, AccountMenuSettingsLink } from '@/components/layout/AccountMenu';
import { isSidebarItemActive, SidebarShell } from '@/components/layout/SidebarShell';
import { AppLoader, CustomButton, CustomModal, IconChip } from '@/components/shared';
import { useNavigation } from '@/contexts/navigation';
import { useUnsavedChangesGuard } from '@/hooks/useUnsavedChangesGuard';
import { createAgentProfileVariable } from '@/services/agentProfileVariableService';
import type {
  AgentDetail,
  AgentDirection,
  AgentFormState,
  ProfileVariableDraft,
  UpdateAgentPayload,
} from '@/types/agent';
import type { PublishGateErrorDetail, ReadinessReport, ReadinessSummary } from '@/types/readiness';
import {
  agentDetailToFormState,
  defaultFormState,
  formStateToCreatePayload,
} from '@/utils/agentFormUtils';
import { categoriesToProbeOnSave } from '@/utils/agentReadinessDiff';
import { mergeReadinessReports, reportToSummary } from '@/services/readinessService';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface AgentEditorShellProps {
  agentType: AgentDirection;
  agentId?: string;
  children: React.ReactNode;
}

/** sessionStorage key holding profile-variable drafts that failed to POST
 * during agent create. The Profile tab reads + clears this on mount for
 * the matching agent (see `ProfileVariablesManager`), so the user's typed
 * values / descriptions survive the redirect from create → edit even when
 * some rows didn't land. */
export const PROFILE_VAR_FLUSH_FAILED_KEY = (agentId: string) =>
  `profile-var-drafts-failed:${agentId}`;

/**
 * POST every profile-variable draft to the freshly-created agent, one at a
 * time. Returns the list of drafts that failed so the caller can surface
 * them to the user — the agent itself is already saved, so we never throw
 * out of here (that would leave the user thinking the create failed).
 *
 * Each draft gets one retry on failure to absorb transient network hiccups;
 * anything still failing is stashed in sessionStorage under
 * ``PROFILE_VAR_FLUSH_FAILED_KEY(agentId)`` with the full draft payload
 * (key / value / description) so the edit-mode Profile tab can offer a
 * one-click retry without the user re-typing.
 */
async function flushProfileVariableDrafts(
  agentId: string,
  drafts: ProfileVariableDraft[],
): Promise<ProfileVariableDraft[]> {
  const failed: ProfileVariableDraft[] = [];
  const postOnce = (draft: ProfileVariableDraft) =>
    createAgentProfileVariable(agentId, {
      key: draft.key,
      value: draft.value,
      description: draft.description ?? undefined,
    });

  for (const draft of drafts) {
    try {
      await postOnce(draft);
      continue;
    } catch (err) {
      console.warn(
        `[profile-variables] flush attempt 1 failed for key="${draft.key}" agent=${agentId}; retrying once`,
        err,
      );
    }
    // Second attempt after a short backoff for transient failures.
    try {
      await new Promise((r) => setTimeout(r, 400));
      await postOnce(draft);
    } catch (err) {
      console.error(
        `[profile-variables] flush failed for key="${draft.key}" agent=${agentId}`,
        err,
      );
      failed.push(draft);
    }
  }

  if (failed.length > 0 && typeof window !== 'undefined') {
    try {
      window.sessionStorage.setItem(
        PROFILE_VAR_FLUSH_FAILED_KEY(agentId),
        JSON.stringify({ drafts: failed, savedAt: Date.now() }),
      );
    } catch (err) {
      // Storage quota / disabled — best-effort only; user still has the toast
      // + console entries above to recover from.
      console.warn('[profile-variables] failed to stash failed drafts', err);
    }
  }
  return failed;
}

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
  const searchParams = useSearchParams();
  const isEditMode = !!agentId;
  const mode = isEditMode ? 'edit' : 'create';

  // The version to restore on first load, captured once from ?version=<n> so
  // it survives a refresh / shared deep-link. Kept in a ref so the load effect
  // doesn't re-run every time we sync the query param back to the URL.
  const initialVersionParamRef = useRef<string | null>(searchParams.get('version'));

  const [, fetchAgent] = useAtom(fetchAgentAtom);
  const [, createAgent] = useAtom(createAgentAtom);
  const [, updateAgent] = useAtom(updateAgentAtom);
  const [, deleteAgent] = useAtom(deleteAgentAtom);
  const [, updateAgentVersion] = useAtom(updateAgentVersionAtom);
  const [, createAgentVersion] = useAtom(createAgentVersionAtom);
  const [, switchActiveAgentVersion] = useAtom(switchActiveAgentVersionAtom);
  const [, deleteAgentVersion] = useAtom(deleteAgentVersionAtom);
  const [, fetchReadinessSummary] = useAtom(fetchAgentReadinessSummaryAtom);
  const [, fetchReadinessReport] = useAtom(fetchAgentReadinessAtom);

  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [createVersionOpen, setCreateVersionOpen] = useState(false);
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  /** Which version is loaded in the form. Null until the agent has loaded. */
  const [viewedConfigId, setViewedConfigId] = useState<string | null>(null);
  const [readinessDrawerOpen, setReadinessDrawerOpen] = useState(false);
  const [readinessSummary, setReadinessSummary] = useState<ReadinessSummary | null>(null);
  /** Last full readiness report we have on hand — deep (from a targeted-deep
   * on save) OR a manual "Run deep test" from the drawer. Kept on the parent
   * so the drawer opens on the SAME data the badge is derived from; without
   * this shared state, the drawer's own shallow fetch would race and
   * disagree with the badge (e.g. badge shows a `tools.reachable` warning
   * that the drawer's shallow refetch can't see). Cleared whenever the
   * viewed config changes so the drawer never renders a stale report from
   * another version. */
  const [readinessReport, setReadinessReport] = useState<ReadinessReport | null>(null);
  /** Mirrors ``readinessReport`` so ``refreshReadinessAfterSave`` — a
   * ``useCallback`` we want to keep stable — can read the latest report
   * (needed to merge successive targeted-deep runs) without listing report
   * state in its deps and getting recreated every render. */
  const readinessReportRef = useRef<ReadinessReport | null>(null);
  useEffect(() => {
    readinessReportRef.current = readinessReport;
  }, [readinessReport]);
  const [readinessLoading, setReadinessLoading] = useState(false);
  /** Bump to force the summary effect to re-run (after save / publish / etc.). */
  const [readinessRefreshKey, setReadinessRefreshKey] = useState(0);
  const bumpReadiness = useCallback(() => setReadinessRefreshKey((k) => k + 1), []);
  /** Keep the header pill (driven by `readinessSummary`) in sync whenever the
   * drawer lands a fresh LIVE report (Refresh / Run deep test). Without this the
   * drawer can show "3 blockers" while the header still reads "Ready". The
   * drawer never calls this for historical run views, so browsing history can't
   * corrupt the badge. Stable identity so the drawer's effects don't re-run. */
  const handleReadinessReportChange = useCallback((report: ReadinessReport | null) => {
    setReadinessReport(report);
    if (report) setReadinessSummary(reportToSummary(report));
  }, []);
  /** Set true immediately after a targeted-deep save lands so the shallow
   * readiness effect can skip its next run — otherwise a slower shallow
   * response overwrites the fresh deep summary and the badge silently drops
   * the warning we just surfaced. Reset by the effect after it skips once. */
  const skipNextShallowRef = useRef(false);
  /** Publish attempted with warnings — parent surfaces a confirm dialog and
   * retries with `force_warnings=true` when the user opts in. */
  const [pendingWarningsReport, setPendingWarningsReport] = useState<ReadinessReport | null>(null);
  const [pendingWarningsConfigId, setPendingWarningsConfigId] = useState<string | null>(null);

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
  // Navigation that stays under the editor base path (switching sections,
  // opening the nested workflow builder) keeps the same persisted form, so no
  // state is lost — it must never trigger the unsaved-changes prompt.
  const isInternalNav = useCallback((dest: string) => dest.startsWith(basePath), [basePath]);

  const { promptOpen, guardedAction, confirmLeave, cancelLeave } = useUnsavedChangesGuard(isDirty, {
    isInternalNavigation: isInternalNav,
  });

  const safeNavigate = useCallback(
    (href: string) => {
      // Internal navigation never loses state, so bypass the guard entirely.
      // (guardedAction only checks dirtiness — it doesn't know the destination.)
      if (isInternalNav(href)) {
        router.push(href);
        return;
      }
      guardedAction(() => router.push(href));
    },
    [guardedAction, isInternalNav, router],
  );
  const navContextValue = useMemo(() => ({ safeNavigate }), [safeNavigate]);
  // Gate call-mode-specific sections (e.g. Contacts) on the LIVE form value so
  // the rail updates the moment the user toggles outbound in Basics; fall back
  // to the URL-derived direction before the form has hydrated.
  const callMode = (watchedValues.agent_type as AgentDirection | undefined) ?? agentType;
  const navGroups = useMemo(
    () => buildAgentNav(basePath, mode, callMode),
    [basePath, mode, callMode],
  );
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
    const raw = initialVersionParamRef.current;
    const parsed = raw != null ? Number(raw) : NaN;
    const requestedVersion = Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
    (async () => {
      try {
        // Single request: ?version=<n> is resolved server-side (no
        // default-fetch-then-config-fetch round trip). Fall back to the live
        // version only if the requested one no longer exists.
        let d: AgentDetail;
        try {
          d =
            requestedVersion != null
              ? await fetchAgent({ agentId, version: requestedVersion })
              : await fetchAgent(agentId);
        } catch (err) {
          if (
            requestedVersion != null &&
            (err as { response?: { status?: number } })?.response?.status === 404
          ) {
            d = await fetchAgent(agentId);
          } else {
            throw err;
          }
        }
        if (cancelled) return;
        applyDetail(d);
        // Initial chip selection = whatever the backend rendered (the requested
        // version, or the live one when no valid version was requested).
        setViewedConfigId(d.config?.id ?? null);
      } catch (err) {
        if (cancelled) return;
        if ((err as { response?: { status?: number } })?.response?.status === 404) {
          showToast.error('Agent not found', 'It may have been deleted.');
          router.replace('/agents');
          return;
        }
        handleApiError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [agentId, applyDetail, fetchAgent, isEditMode, router]);

  // ─── readiness summary (drives header pill) ───────────────────────────────
  // Refetches when the agent id, the currently-loaded config id, or the
  // explicit bump key change. Edit-based freshness on the backend means the
  // majority of calls short-circuit against a stored snapshot — cheap.
  //
  // Race protection: after a save runs a targeted-deep probe (see
  // `refreshReadinessAfterSave`) we already have the freshest, most-detailed
  // report in state. The subsequent `detail.config.id` change would fire this
  // effect and clobber it with a shallow re-read. The `skipNextShallowRef`
  // guard skips exactly one fire so the deep result stays visible.
  useEffect(() => {
    if (!isEditMode || !agentId) return;
    if (skipNextShallowRef.current) {
      skipNextShallowRef.current = false;
      return;
    }
    const loadedConfigId = detail?.config?.id ?? undefined;
    let cancelled = false;
    setReadinessLoading(true);
    (async () => {
      try {
        const summary = await fetchReadinessSummary({
          agentId,
          configId: loadedConfigId,
          trigger: 'editor_load',
        });
        if (cancelled) return;
        setReadinessSummary(summary);
        // Shallow fetches only return a summary, not a full report. Drop any
        // stale full report so the drawer refetches instead of rendering an
        // older deep report against a possibly-newer config.
        setReadinessReport(null);
      } catch {
        // Non-critical UI — never toast; badge falls back to the "error" pill.
        if (!cancelled) setReadinessSummary(null);
      } finally {
        if (!cancelled) setReadinessLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isEditMode, agentId, detail?.config?.id, readinessRefreshKey, fetchReadinessSummary]);

  /** Version number of the currently-viewed version (the chip selection). */
  const viewedVersionNum = useMemo(
    () => (detail?.versions ?? []).find((v) => v.id === viewedConfigId)?.version ?? null,
    [detail?.versions, viewedConfigId],
  );

  // Keep ?version=<n> in the URL in sync with the viewed version so a refresh or
  // shared link reopens the same version. Also re-applies the param after a
  // section switch (nav links carry no query) — self-healing, no reload since
  // the load effect doesn't depend on the query. Skipped on the full-screen
  // workflow builder sub-route.
  useEffect(() => {
    if (!isEditMode || loading || viewedVersionNum == null) return;
    if (/\/workflow\/[^/]+$/.test(pathname)) return;
    if (searchParams.get('version') === String(viewedVersionNum)) return;
    const qs = new URLSearchParams(Array.from(searchParams.entries()));
    qs.set('version', String(viewedVersionNum));
    router.replace(`${pathname}?${qs.toString()}`, { scroll: false });
  }, [isEditMode, loading, viewedVersionNum, pathname, searchParams, router]);

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
          if (settingsKey === 'llm_settings') router.push(`${basePath}/setup`);
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

  /** Refresh the readiness badge after a save.
   *
   * If any resource-owning category (LLM/STT/TTS/tools/MCP/KB/phone) changed
   * we fire a **targeted deep** probe — live-checks only those categories and
   * skips the others as SKIPPED. Prompt-only edits (or anything that touches
   * no resource category) fall back to the shallow bump path so we don't
   * burn provider tokens on non-actionable saves.
   *
   * Fire-and-forget by design: 429s, network flakes, or backend errors
   * silently degrade to a shallow refresh — the save UX must never wait on
   * or fail because of readiness. */
  const refreshReadinessAfterSave = useCallback(
    (prev: AgentFormState, next: AgentFormState, configId: string | null | undefined) => {
      const changed = categoriesToProbeOnSave(prev, next);
      if (changed.length === 0 || !configId) {
        bumpReadiness();
        return;
      }
      // Suppress the next shallow-effect fire so it doesn't overwrite the
      // richer deep report we're about to install. The ref is armed BEFORE
      // the fetch so it survives the intermediate `applyDetail` → config-id
      // change that would otherwise trigger the effect.
      skipNextShallowRef.current = true;
      void (async () => {
        try {
          const report = await fetchReadinessReport({
            agentId: agentId!,
            depth: 'deep',
            configId,
            trigger: 'field_change',
            categories: changed,
          });
          // Merge with the previous report so categories we didn't just
          // re-probe (SKIPPED because unchanged) keep their last-known real
          // status — otherwise a second consecutive save on a different
          // category would silently drop the previous save's warnings from
          // the badge and the drawer.
          const merged = mergeReadinessReports(readinessReportRef.current, report);
          // Both the badge (summary) and the drawer (full report) render off
          // the same landed data — no drift between "warning shown above" and
          // "no warning shown inside".
          setReadinessSummary(reportToSummary(merged));
          setReadinessReport(merged);
        } catch {
          // Deep failed — let the shallow effect run so the badge still
          // refreshes off the DB fast-path.
          skipNextShallowRef.current = false;
          bumpReadiness();
        }
      })();
    },
    [agentId, bumpReadiness, fetchReadinessReport],
  );

  // ─── save / delete / publish / create-version ─────────────────────────────
  /** Save button handler — validates, then either creates the agent (create
   *  flow) or mutates the loaded version in place (edit flow). Save never
   *  spawns a new draft; that's the "Create version" button's job. */
  const handleSave = useCallback(async () => {
    const valid = await methods.trigger();
    if (!valid) {
      // Stay on the current tab so the user sees the highlighted invalid
      // field. Previously this unconditionally routed to `/basics`, hiding
      // the actual error (e.g. an invalid Voice-tab field would silently
      // teleport the user to Basics with nothing visibly wrong).
      const errorFields = Object.keys(methods.formState.errors);
      showToast.error(
        'Cannot save',
        errorFields.length
          ? `Fix ${errorFields.length === 1 ? 'the highlighted error' : `${errorFields.length} highlighted errors`} and try again.`
          : 'Fix the highlighted errors and try again.',
      );
      return;
    }
    // No edits → nothing to write. The create flow always proceeds because
    // the agent itself doesn't exist yet.
    if (isEditMode && agentId && isEqual(methods.getValues(), loadedBaselineRef.current)) {
      showToast.success('No changes', 'Nothing to save.');
      return;
    }
    const values = methods.getValues();
    setSaving(true);
    try {
      if (!isEditMode || !agentId) {
        const created = await createAgent(formStateToCreatePayload(values));
        // Flush any profile-variable drafts to the newly-created agent BEFORE
        // navigating. Failures don't block the redirect — the agent itself is
        // saved; the user can retry from the (now edit-mode) Profile tab.
        const failed = await flushProfileVariableDrafts(
          created.id,
          values.profile_variable_drafts ?? [],
        );
        if (failed.length > 0) {
          showToast.error(
            `Agent created, but ${failed.length} profile variable(s) failed to save: ${failed
              .map((f) => f.key)
              .join(', ')}. Open the Profile tab to retry.`,
          );
        } else {
          showToast.success('Agent created');
        }
        methods.reset({ ...values, profile_variable_drafts: [] });
        router.push(`/agents/edit/${created.agent_type}/${created.id}/setup`);
        return;
      }

      // Edit flow — split the save into two endpoints:
      //   1. Root agent fields (name/description/agent_type/is_active) live
      //      on the ``agents`` row itself and are NOT part of any version.
      //      Send their diff through PUT /update_agent.
      //   2. Everything else (config + attachments) is version-scoped — goes
      //      through PUT /update_version against ``source_config_id``.
      const full = formStateToCreatePayload(values);
      const baseline = loadedBaselineRef.current;
      const rootChanges: UpdateAgentPayload = {};
      if (values.name.trim() !== baseline.name.trim()) {
        rootChanges.name = values.name.trim();
      }
      const nextDesc = values.description?.trim() ?? '';
      const prevDesc = baseline.description?.trim() ?? '';
      if (nextDesc !== prevDesc) {
        rootChanges.description = nextDesc || null;
      }
      if (values.agent_type !== baseline.agent_type) {
        rootChanges.agent_type = values.agent_type;
      }
      if (values.is_active !== baseline.is_active) {
        rootChanges.is_active = values.is_active;
      }
      if (Object.keys(rootChanges).length > 0) {
        await updateAgent({ id: agentId, values: rootChanges });
      }

      // Config: send only fields that actually changed. Prevents
      // AgentConfigRequest's ``_require_workflow_when_workflow_mode`` validator
      // from firing on a saved-but-stale ``mode: 'workflow'`` / ``workflow_id: null``
      // pair when the user is saving unrelated tool/MCP/OAuth changes. Same
      // code path for both tool and MCP saves.
      const cfgDiff: Record<string, unknown> = {};
      if (full.config) {
        (Object.keys(full.config) as (keyof typeof full.config)[]).forEach((key) => {
          if (!isEqual(full.config![key], baseline.config[key])) {
            cfgDiff[key] = full.config![key];
          }
        });
      }

      const updated = await updateAgentVersion({
        agentId,
        values: {
          ...(Object.keys(cfgDiff).length > 0 && { config: cfgDiff as typeof full.config }),
          tool_ids: full.tool_ids,
          mcp_server_ids: full.mcp_server_ids,
          upload_ids: full.upload_ids,
          phone_numbers: full.phone_numbers,
          web_channel_ids: full.web_channel_ids,
          tool_oauth_overrides: full.tool_oauth_overrides,
          mcp_server_oauth_overrides: full.mcp_server_oauth_overrides,
          source_config_id: detail?.config?.id ?? null,
        },
      });
      applyDetail(updated);
      refreshReadinessAfterSave(baseline, values, updated.config?.id ?? null);
      showToast.success(
        'Changes saved',
        updated.config?.version != null ? `v${updated.config.version} was updated.` : undefined,
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
    refreshReadinessAfterSave,
    router,
    updateAgent,
    updateAgentVersion,
  ]);

  /** Create-version modal handler. Spawns a new draft either by cloning a
   *  picked version (``mode === 'copy'``) or starting fresh (no source).
   *  After success the editor jumps to the new draft so the user can edit
   *  it immediately — Save then mutates that draft in place. */
  const handleCreateVersion = useCallback(
    async ({ mode: createMode, sourceConfigId }: CreateVersionSelection) => {
      if (!agentId) return;
      setCreatingVersion(true);
      try {
        const updated = await createAgentVersion({
          agentId,
          values: {
            source_config_id: createMode === 'copy' ? sourceConfigId : null,
            from_scratch: createMode === 'fresh',
          },
        });
        applyDetail(updated);
        // Move the chip to the new draft so the version dropdown reflects
        // what the form is rendering. Without this, the chip would stay
        // pinned to the previously-loaded version while the form shows the
        // new draft — a confusing mismatch when the user is about to edit.
        const newConfigId = updated.config?.id ?? null;
        if (newConfigId) setViewedConfigId(newConfigId);
        bumpReadiness();
        setCreateVersionOpen(false);
        showToast.success(
          'Version created',
          updated.config?.version != null
            ? `v${updated.config.version} is now loaded — click Publish when ready.`
            : undefined,
        );
      } catch (err) {
        handleApiError(err);
      } finally {
        setCreatingVersion(false);
      }
    },
    [agentId, applyDetail, bumpReadiness, createAgentVersion],
  );

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
    async (configId: string, forceWarnings = false) => {
      if (!agentId || !configId) return;
      setPublishing(true);
      try {
        const updated = await switchActiveAgentVersion({
          agentId,
          configId,
          forceWarnings,
        });
        applyDetail(updated);
        // Chip follows the published version once promotion succeeds — so the
        // user lands on the version they just made live.
        setViewedConfigId(updated.config?.id ?? configId);
        bumpReadiness();
        const v = updated.versions?.find((row) => row.id === configId)?.version;
        showToast.success(
          'Version published',
          v != null ? `v${v} is now serving calls.` : undefined,
        );
        setPublishOpen(false);
        setPendingWarningsReport(null);
        setPendingWarningsConfigId(null);
      } catch (err) {
        // Readiness-gate rejection carries a structured detail payload —
        // interpret it here so the UI can either surface an explicit
        // confirmation dialog (warnings) or a hard error toast (blockers).
        const gate = extractGateDetail(err);
        if (gate?.reason === 'readiness_warnings') {
          setPendingWarningsReport(gate.report);
          setPendingWarningsConfigId(configId);
        } else if (gate?.reason === 'readiness_blocked') {
          bumpReadiness(); // refresh badge so the user sees the fresh blockers
          showToast.error(
            'Cannot publish',
            gate.message ??
              'This version has blockers. Open the readiness drawer to see what to fix.',
          );
        } else {
          // Leave the modal open on generic errors — the user can retry
          // without losing the version-selector context.
          handleApiError(err);
        }
      } finally {
        setPublishing(false);
      }
    },
    [agentId, applyDetail, bumpReadiness, switchActiveAgentVersion],
  );

  const handleConfirmPublishWithWarnings = useCallback(async () => {
    if (!pendingWarningsConfigId) return;
    await handlePublish(pendingWarningsConfigId, true);
  }, [handlePublish, pendingWarningsConfigId]);

  const handleDismissWarningsDialog = useCallback(() => {
    setPendingWarningsReport(null);
    setPendingWarningsConfigId(null);
  }, []);

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
        bumpReadiness();
      } catch (err) {
        handleApiError(err);
      }
    },
    [agentId, applyDetail, bumpReadiness, deleteAgentVersion, fetchAgent, viewedConfigId],
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

  // Stable target for the save-as-template dialog — a fresh object literal on
  // every render would retrigger the modal's name-seeding effect and wipe the
  // user's input. Null while the dialog is closed.
  const saveTemplateTarget = useMemo(
    () => (isEditMode && agentId && saveTemplateOpen ? { id: agentId, name: agentName } : null),
    [isEditMode, agentId, saveTemplateOpen, agentName],
  );

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
      if (action === 'create-version') {
        // Creating a version also reloads the form with the new draft, so
        // any unsaved edits on the currently-loaded version would be lost.
        // Same guard as Publish.
        guardedAction(() => setCreateVersionOpen(true));
        return;
      }
      if (action === 'save-as-template') {
        // Snapshots the live config server-side (like clone) — it neither
        // reads nor reloads the form, so no discard guard is needed. Just open
        // the naming dialog.
        setSaveTemplateOpen(true);
        return;
      }
      if (action === 'test') {
        setReadinessDrawerOpen(true);
        return;
      }
      if (action === 'delete') {
        setDeleteOpen(true);
        return;
      }
      void handleSave();
    },
    [guardedAction, handleSave],
  );

  // The nested workflow builder (/agents/edit/<type>/<id>/workflow/<wfId>) is a
  // full-canvas editor with its own toolbar. Render it edge-to-edge — no editor
  // rail, save-bar or max-width wrapper — while keeping the form/nav/editor
  // providers mounted so the agent's unsaved state survives the round-trip and
  // returning to a section counts as internal navigation (no discard prompt).
  const isBuilderRoute = /\/workflow\/[^/]+$/.test(pathname);
  // Call History, Contacts and Schedule host full-width tables + toolbars — they need
  // the entire content width. The form sections (Basics, Prompt, …) stay in the
  // narrow, centered max-w-3xl column that reads better for forms.
  const isWideSection = /\/(call-history|contacts|schedule|llm-evals)$/.test(pathname);
  if (isBuilderRoute) {
    return (
      <FormProvider {...methods}>
        <AgentFormNavProvider value={navContextValue}>
          <AgentEditorProvider value={editorContextValue}>
            <div className="h-full w-full min-w-0 bg-background">{children}</div>
          </AgentEditorProvider>
        </AgentFormNavProvider>
      </FormProvider>
    );
  }

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
              footer={(collapsed) => (
                <AccountMenu collapsed={collapsed}>
                  <AccountMenuSettingsLink />
                </AccountMenu>
              )}
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
                  'relative flex shrink-0 items-center gap-3 overflow-hidden border-b border-border/60 px-5 py-5',
                  HEADER_TINT[agentType],
                )}
              >
                <IconChip
                  tone={DIRECTION_TONES[agentType]}
                  size="xl"
                  interactive
                  className="text-lg font-semibold tracking-tight"
                >
                  <span aria-hidden>{agentInitial}</span>
                </IconChip>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
                      {agentName}
                    </h1>
                    <AgentTypeBadge agentType={agentType} size="sm" />
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
                <div className="flex shrink-0 items-center gap-4">
                  {isEditMode && (
                    <ReadinessBadge
                      status={
                        readinessLoading && !readinessSummary
                          ? 'loading'
                          : readinessSummary
                            ? readinessSummary.overall_status
                            : 'error'
                      }
                      blockerCount={readinessSummary?.blocker_count ?? 0}
                      warningCount={readinessSummary?.warning_count ?? 0}
                      size="md"
                      onClick={() => setReadinessDrawerOpen(true)}
                      aria-label="Open agent readiness"
                    />
                  )}
                  {isEditMode && versions.length > 0 && (
                    <AgentVersionSelector
                      versions={versions}
                      selectedConfigId={viewedConfigId}
                      onSelect={safeViewVersion}
                      onDelete={handleDeleteVersion}
                      disabled={loading || saving || publishing}
                    />
                  )}
                  <AgentSaveActions
                    mode={isEditMode ? 'edit' : 'create'}
                    canPublish={canPublish}
                    saving={saving}
                    publishing={publishing}
                    creatingVersion={creatingVersion}
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
                  <AppLoader className="min-h-0 h-full" />
                ) : (
                  <div
                    className={cn(
                      'mx-auto h-full',
                      isWideSection ? 'w-full max-w-none' : 'max-w-3xl',
                    )}
                  >
                    {children}
                  </div>
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
              onConfirm={(configId) => handlePublish(configId)}
              versions={versions}
              publishedVersionId={publishedVersion?.id ?? null}
              loading={publishing}
              agentId={agentId}
            />

            <CreateVersionModal
              open={createVersionOpen}
              // Ignore close requests while the create call is in flight so
              // the dialog can't be dismissed mid-write.
              onClose={() => {
                if (!creatingVersion) setCreateVersionOpen(false);
              }}
              onConfirm={handleCreateVersion}
              versions={versions}
              publishedVersionId={publishedVersion?.id ?? null}
              loading={creatingVersion}
            />

            <SaveAsTemplateModal
              agent={saveTemplateTarget}
              onClose={() => setSaveTemplateOpen(false)}
            />

            {isEditMode && agentId && (
              <ReadinessDrawer
                open={readinessDrawerOpen}
                onClose={() => setReadinessDrawerOpen(false)}
                agentId={agentId}
                configId={detail?.config?.id ?? null}
                trigger="editor_load"
                initialReport={readinessReport}
                onReportChange={handleReadinessReportChange}
              />
            )}

            <ReadinessConfirmDialog
              open={pendingWarningsReport !== null}
              onClose={handleDismissWarningsDialog}
              report={pendingWarningsReport}
              onConfirm={handleConfirmPublishWithWarnings}
              loading={publishing}
            />
          </div>
        </AgentEditorProvider>
      </AgentFormNavProvider>
    </FormProvider>
  );
}

/** Peek at an Axios error and return the backend's readiness-gate detail if
 * present. Returns null for non-gate errors (network, 500, etc.) so the caller
 * can fall back to the generic error toast. */
function extractGateDetail(err: unknown): PublishGateErrorDetail | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (!detail || typeof detail !== 'object') return null;
  const reason = (detail as { reason?: unknown }).reason;
  if (reason !== 'readiness_blocked' && reason !== 'readiness_warnings') return null;
  return detail as PublishGateErrorDetail;
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
