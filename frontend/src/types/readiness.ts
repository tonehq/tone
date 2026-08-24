/**
 * Types mirroring the backend readiness API. See `core/services/readiness/schemas.py`.
 *
 * Kept as an isolated module so both the service, atoms, and every UI component
 * can import from one canonical source. If the backend adds a new severity /
 * status / category, this is the ONLY file to change on the frontend.
 */

export type ReadinessDepth = 'shallow' | 'deep';

export type ReadinessOverallStatus = 'ready' | 'ready_with_warnings' | 'not_ready';

export type ReadinessSeverity = 'blocker' | 'warning' | 'info';

export type ReadinessCheckStatus = 'pass' | 'fail' | 'skipped';

export type ReadinessCategory =
  | 'agent'
  | 'llm'
  | 'stt'
  | 'tts'
  | 'phone'
  | 'transport'
  | 'tools'
  | 'knowledge_bases'
  | 'mcp_servers';

/** Free-form label the frontend sends so the backend can slice analytics by
 * how a check was triggered. Not enum-typed on either side — new triggers can
 * be added without a coordinated deploy. */
export type ReadinessTrigger =
  | 'editor_load'
  | 'field_change'
  | 'publish_gate'
  | 'test_button'
  | 'list_page'
  | 'api';

export interface ReadinessResourceRef {
  type: string;
  id: string;
}

export interface ReadinessCheckResult {
  check_id: string;
  category: ReadinessCategory;
  severity: ReadinessSeverity;
  status: ReadinessCheckStatus;
  message: string;
  remediation: string | null;
  deep_link: string | null;
  resource_ref: ReadinessResourceRef | null;
  skip_reason: string | null;
}

export interface ReadinessSummaryCounts {
  blockers: number;
  warnings: number;
  info: number;
  passed: number;
  skipped: number;
}

export interface ReadinessReport {
  agent_id: string;
  config_id: string | null;
  depth: ReadinessDepth;
  overall_status: ReadinessOverallStatus;
  summary: ReadinessSummaryCounts;
  checks: ReadinessCheckResult[];
  generated_at: string;
  /** Wall-clock start of the run (ISO-8601). Null on older reports. */
  started_at?: string | null;
  /** Per-agent monotonically increasing run counter. Null when not persisted. */
  run_number?: number | null;
}

/** One row in the readiness run-history dropdown. Metadata only — the full
 * `checks` list is fetched per-run via GET /agent/{id}/readiness/runs/{n}. */
export interface ReadinessRunListItem {
  run_number: number;
  depth: ReadinessDepth;
  overall_status: ReadinessOverallStatus;
  config_id: string | null;
  trigger: string;
  blocker_count: number;
  warning_count: number;
  info_count: number;
  passed_count: number;
  skipped_count: number;
  started_at: string | null;
  computed_at: string;
  duration_ms: number | null;
}

export interface ReadinessRunList {
  items: ReadinessRunListItem[];
}

export interface ReadinessSummary {
  agent_id: string;
  config_id: string | null;
  overall_status: ReadinessOverallStatus;
  blocker_count: number;
  warning_count: number;
  info_count: number;
}

/** Body shape the backend expects for `POST /agent/{id}/switch_active_version`
 * when the readiness gate rejects the publish. `report` mirrors ReadinessReport. */
export interface PublishGateErrorDetail {
  reason: 'readiness_blocked' | 'readiness_warnings';
  message: string;
  report: ReadinessReport;
}
