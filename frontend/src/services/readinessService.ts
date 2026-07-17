import axiosInstance from '@/utils/axios';
import type {
  ReadinessCategory,
  ReadinessDepth,
  ReadinessReport,
  ReadinessSummary,
  ReadinessTrigger,
} from '@/types/readiness';

/** Body of POST /agent/{id}/readiness. Optional fields are omitted when
 * unset so backend defaults apply. */
interface ReadinessRequestBody {
  depth: ReadinessDepth;
  config_id?: string;
  trigger?: string;
  /** Targeted-deep filter — only meaningful when depth=`deep`. Backend probes
   * only these categories live; the rest return SKIPPED. Used by save flows
   * that know exactly which resources changed. */
  categories?: ReadinessCategory[];
}

/** Derive a badge-shaped {@link ReadinessSummary} from a full report. Kept
 * client-side so a targeted-deep POST /readiness call can drive the same UI
 * atom the shallow GET /readiness/summary call feeds — no extra round-trip. */
export const reportToSummary = (report: ReadinessReport): ReadinessSummary => ({
  agent_id: report.agent_id,
  config_id: report.config_id,
  overall_status: report.overall_status,
  blocker_count: report.summary.blockers,
  warning_count: report.summary.warnings,
  info_count: report.summary.info,
});

/** Marker the backend runner sets as the skip reason for deep checks it
 * filtered out because the caller only requested a subset of categories.
 * Duplicated in `core/services/readiness/runner.py::_execute_all`. Kept in
 * sync manually — if the backend copy changes, this constant must follow.
 * Substring-matched to avoid coupling to the exact templated category name. */
const TARGETED_DEEP_SKIP_MARKER = 'Not re-probed on this save';

/**
 * Merge a fresh targeted-deep report with the previous one.
 *
 * The targeted-deep flow (see `refreshReadinessAfterSave` in
 * `AgentEditorShell`) asks the backend to only live-probe the categories the
 * user just touched. Every other deep check comes back SKIPPED with a
 * dedicated marker so the report shape stays uniform. Without merging, a
 * second consecutive save with a different category would appear to "clear"
 * the previous save's warnings — e.g. attach a broken tool → save (deep
 * probes tools, FAIL surfaces), change LLM → save (deep re-probes LLM,
 * tool check comes back SKIPPED, tool FAIL vanishes from the badge).
 *
 * This merge preserves the last known real status for every check the new
 * report didn't actually re-run, then recomputes summary counts and
 * `overall_status` so the badge reflects the union.
 */
export const mergeReadinessReports = (
  prev: ReadinessReport | null,
  next: ReadinessReport,
): ReadinessReport => {
  if (!prev) return next;

  const prevByCheckId = new Map(prev.checks.map((c) => [c.check_id, c]));
  const mergedChecks = next.checks.map((c) => {
    const wasFilteredOut =
      c.status === 'skipped' &&
      (c.skip_reason ?? c.message ?? '').includes(TARGETED_DEEP_SKIP_MARKER);
    if (!wasFilteredOut) return c;
    const prior = prevByCheckId.get(c.check_id);
    // Only preserve when the prior entry had a "real" outcome — a prior
    // SKIPPED entry carries no new information.
    if (prior && prior.status !== 'skipped') return prior;
    return c;
  });

  let blockers = 0;
  let warnings = 0;
  let info = 0;
  let passed = 0;
  let skipped = 0;
  for (const c of mergedChecks) {
    if (c.status === 'pass') passed += 1;
    else if (c.status === 'skipped') skipped += 1;
    else if (c.status === 'fail') {
      if (c.severity === 'blocker') blockers += 1;
      else if (c.severity === 'warning') warnings += 1;
      else info += 1;
    }
  }
  const overall_status: ReadinessReport['overall_status'] =
    blockers > 0 ? 'not_ready' : warnings > 0 ? 'ready_with_warnings' : 'ready';

  return {
    ...next,
    overall_status,
    summary: { blockers, warnings, info, passed, skipped },
    checks: mergedChecks,
  };
};

/**
 * Run a readiness check for one agent + (optionally explicit) config.
 * - Depth `shallow`: DB-only, safe on hot paths.
 * - Depth `deep`: hits real providers; rate-limited to 1/min per agent server-side.
 *
 * Errors bubble up unmodified so the caller can inspect status + payload
 * (needed by the publish flow to distinguish `readiness_blocked` vs
 * `readiness_warnings`). Non-publish callers should wrap in `handleApiError`.
 */
export const getAgentReadiness = async (
  agentId: string,
  depth: ReadinessDepth,
  configId?: string,
  trigger?: ReadinessTrigger | string,
  categories?: ReadinessCategory[],
): Promise<ReadinessReport> => {
  const body: ReadinessRequestBody = { depth };
  if (configId) body.config_id = configId;
  if (trigger) body.trigger = trigger;
  if (categories && categories.length > 0) body.categories = categories;
  const res = await axiosInstance.post<ReadinessReport>(`/agent/${agentId}/readiness`, body);
  return res.data;
};

/**
 * Cheap summary shape for the agent list badge. Always Shallow — the badge
 * doesn't need per-check detail. Trigger defaults to `list_page` if omitted
 * so backend analytics can distinguish list impressions from editor loads.
 */
export const getAgentReadinessSummary = async (
  agentId: string,
  configId?: string,
  trigger: ReadinessTrigger | string = 'list_page',
): Promise<ReadinessSummary> => {
  const res = await axiosInstance.get<ReadinessSummary>(`/agent/${agentId}/readiness/summary`, {
    params: { ...(configId ? { config_id: configId } : {}), trigger },
  });
  return res.data;
};
