import axiosInstance from '@/utils/axios';
import type {
  ReadinessCategory,
  ReadinessDepth,
  ReadinessReport,
  ReadinessRunList,
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
  /** Force a fresh run + persisted event, bypassing the backend read-through
   * caches. Set by the "Run deep test" button so each explicit run appears as a
   * new entry in the run-history list. */
  force?: boolean;
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
 * Mirrors `TARGETED_DEEP_SKIP_PREFIX` in `core/services/readiness/runner.py`.
 * The coupling is enforced by `test_readiness_frontend_contract.py` — that test
 * fails if the backend value changes, so this copy can't silently drift.
 * Substring-matched to avoid coupling to the exact templated category name. */
const TARGETED_DEEP_SKIP_MARKER = 'Not re-probed on this save';

/**
 * Pairs of (shallow heads-up check-id, authoritative deep check-id). When the
 * deep check produced a real result for a resource, the shallow heads-up is
 * redundant and dropped. MIRRORS `core/services/readiness/consolidation.py`
 * (`_SUPERSEDED_BY_DEEP`) — the backend already de-duplicates fresh reports;
 * this is applied again after a targeted-deep MERGE (which can re-introduce a
 * carried-forward deep row next to a fresh shallow heads-up). The coupling is
 * enforced by `test_readiness_frontend_contract.py`, which fails if the backend
 * pairs change, so this copy can't silently drift. check-ids are matched by
 * prefix so per-resource ids match.
 */
const DEEP_SUPERSEDES_SHALLOW: ReadonlyArray<readonly [string, string]> = [
  ['mcp_servers.oauth_token_valid', 'mcp_servers.reachable'],
  ['tools.oauth_token_valid', 'tools.reachable'],
];

const matchesCheckId = (id: string, prefix: string): boolean =>
  id === prefix || id.startsWith(`${prefix}:`);

/** Drop shallow heads-up rows the deep probe has already answered. Pure. */
const suppressRedundantShallowChecks = (
  checks: ReadinessReport['checks'],
): ReadinessReport['checks'] => {
  const ranDeep = new Set<string>();
  for (const c of checks) {
    if (c.status === 'skipped') continue;
    for (const [, deep] of DEEP_SUPERSEDES_SHALLOW) {
      if (matchesCheckId(c.check_id, deep)) ranDeep.add(deep);
    }
  }
  if (ranDeep.size === 0) return checks;
  const superseded = DEEP_SUPERSEDES_SHALLOW.filter(([, deep]) => ranDeep.has(deep)).map(
    ([headsup]) => headsup,
  );
  return checks.filter((c) => !superseded.some((prefix) => matchesCheckId(c.check_id, prefix)));
};

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
  const nextIds = new Set(next.checks.map((c) => c.check_id));

  const isFilteredMarker = (c: ReadinessReport['checks'][number]): boolean =>
    c.status === 'skipped' &&
    (c.skip_reason ?? c.message ?? '').includes(TARGETED_DEEP_SKIP_MARKER);

  // Bare check_ids the new run left unprobed (targeted-deep save that didn't
  // touch that category). A per-resource check (e.g. one row per MCP server)
  // emits rows keyed `${bareId}:${resourceId}` when it DOES run, but only the
  // bare marker row when it's filtered — so we match prior per-resource rows
  // by prefix, not exact id.
  const filteredBareIds = next.checks.filter(isFilteredMarker).map((c) => c.check_id);
  const belongsToFilteredCheck = (id: string): boolean =>
    filteredBareIds.some((bare) => id === bare || id.startsWith(`${bare}:`));

  const mergedChecks: ReadinessReport['checks'] = [];
  for (const c of next.checks) {
    if (!isFilteredMarker(c)) {
      mergedChecks.push(c);
      continue;
    }
    // Stable-id check whose category was untouched: restore the prior real
    // outcome under the SAME id.
    const prior = prevByCheckId.get(c.check_id);
    if (prior && prior.status !== 'skipped') {
      mergedChecks.push(prior);
      continue;
    }
    // Per-resource check (dynamic ids): drop the bare marker only when the
    // prior report actually has per-resource rows to carry forward below —
    // otherwise keep the marker so the category isn't silently empty.
    const hasPriorResourceRows = prev.checks.some(
      (p) =>
        p.status !== 'skipped' &&
        !nextIds.has(p.check_id) &&
        p.check_id.startsWith(`${c.check_id}:`),
    );
    if (!hasPriorResourceRows) mergedChecks.push(c);
  }

  // Carry forward prior per-resource rows whose check was filtered out this
  // run and that have no counterpart in the new report. Without this, a
  // targeted-deep save that didn't touch MCP would drop previously-failing
  // per-server MCP rows from the badge until the next deep test.
  for (const p of prev.checks) {
    if (p.status !== 'skipped' && !nextIds.has(p.check_id) && belongsToFilteredCheck(p.check_id)) {
      mergedChecks.push(p);
    }
  }

  // Re-apply the backend's cross-check de-duplication: a carried-forward deep
  // row (e.g. "MCP can't be reached") next to a fresh shallow heads-up
  // ("token may be expired") for the same resource would show the same problem
  // twice. Run BEFORE counting so the badge numbers match what's rendered.
  const dedupedChecks = suppressRedundantShallowChecks(mergedChecks);

  let blockers = 0;
  let warnings = 0;
  let info = 0;
  let passed = 0;
  let skipped = 0;
  for (const c of dedupedChecks) {
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
    checks: dedupedChecks,
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
  force?: boolean,
): Promise<ReadinessReport> => {
  const body: ReadinessRequestBody = { depth };
  if (configId) body.config_id = configId;
  if (trigger) body.trigger = trigger;
  if (categories && categories.length > 0) body.categories = categories;
  if (force) body.force = true;
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

/**
 * List past deep readiness runs (newest first) for the run-history dropdown.
 * Metadata only — call {@link getAgentReadinessRun} to load one run's checks.
 */
export const listAgentReadinessRuns = async (
  agentId: string,
  limit = 20,
): Promise<ReadinessRunList> => {
  const res = await axiosInstance.get<ReadinessRunList>(`/agent/${agentId}/readiness/runs`, {
    params: { limit },
  });
  return res.data;
};

/** Fetch the full stored report (with checks) for one past run. */
export const getAgentReadinessRun = async (
  agentId: string,
  runNumber: number,
): Promise<ReadinessReport> => {
  const res = await axiosInstance.get<ReadinessReport>(
    `/agent/${agentId}/readiness/runs/${runNumber}`,
  );
  return res.data;
};
