import type { ToolExecution, ToolExecutionStatus } from '@/types/callLog';

/** Sentinel for the "show everything" choice in the tool-name filter. */
export const ALL_TOOLS = 'all';

/** Sorted list of unique tool names present in this call's executions. Used
 *  by the filter row so users can pick a specific tool to drill into. */
export function uniqueToolNames(rows: ToolExecution[]): string[] {
  const set = new Set<string>();
  for (const row of rows) set.add(row.tool_name);
  return Array.from(set).sort();
}

/** Pretty label for a tool type — falls back to title-cased raw value. */
export function toolTypeLabel(type: ToolExecution['tool_type']): string {
  switch (type) {
    case 'custom':
      return 'Custom';
    case 'mcp':
      return 'MCP';
    case 'send_sms':
      return 'SMS';
    case 'google_calendar':
      return 'Calendar';
    case 'read_document':
      return 'Document';
    case 'built_in':
      return 'Built-in';
    default:
      return type ? type.replace(/_/g, ' ') : 'Unknown';
  }
}

/** Tailwind classes for the colored chip behind a tool-type label. */
export function toolTypeChipClasses(type: ToolExecution['tool_type']): string {
  switch (type) {
    case 'mcp':
      return 'bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300';
    case 'custom':
      return 'bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300';
    case 'send_sms':
    case 'google_calendar':
    case 'read_document':
    case 'built_in':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

/** Tailwind classes + label for the lifecycle status pill.
 *
 *  Covers the full LLM proposal lifecycle:
 *  - `proposed`  — LLM asked for the tool but no handler ran. Amber, so users
 *                  can tell a hallucinated tool name apart from a successful run.
 *  - `cancelled` — proposed and dispatched, but killed mid-execution (barge-in).
 *                  Muted grey — expected during natural conversation flow.
 *  - `success`   — handler completed cleanly. Emerald.
 *  - `error`     — handler ran but returned/raised an error. Rose. */
export function statusPill(status: ToolExecution['status']): { label: string; className: string } {
  if (status === 'success') {
    return {
      label: 'Success',
      className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
    };
  }
  if (status === 'error') {
    return {
      label: 'Error',
      className: 'bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
    };
  }
  if (status === 'proposed') {
    return {
      label: 'Proposed',
      className: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
    };
  }
  if (status === 'cancelled') {
    return {
      label: 'Cancelled',
      className: 'bg-slate-100 text-slate-700 dark:bg-slate-500/15 dark:text-slate-300',
    };
  }
  return {
    label: status ?? 'Unknown',
    className: 'bg-muted text-muted-foreground',
  };
}

export type DurationTone = 'neutral' | 'good' | 'warn' | 'bad';

/** Format a duration in milliseconds, color-graded by latency thresholds.
 *  Null / missing values are returned as ``neutral`` so the UI doesn't paint
 *  them in the success color. */
export function formatDuration(ms: number | null): { text: string; tone: DurationTone } {
  if (ms == null) return { text: '—', tone: 'neutral' };
  if (ms < 500) return { text: `${ms} ms`, tone: 'good' };
  if (ms < 1500) return { text: `${ms} ms`, tone: 'warn' };
  return { text: `${ms} ms`, tone: 'bad' };
}

export function durationToneClass(tone: DurationTone): string {
  switch (tone) {
    case 'good':
      return 'text-emerald-600 dark:text-emerald-400';
    case 'warn':
      return 'text-amber-600 dark:text-amber-400';
    case 'bad':
      return 'text-rose-600 dark:text-rose-400';
    case 'neutral':
    default:
      return 'text-muted-foreground';
  }
}

/** Unified "endpoint" the agent actually reached out to. Custom/built-in
 *  tools use the configured webhook URL; MCP tools use their server URL.
 *  Returns `null` when no endpoint applies (e.g. code-defined built-ins). */
export function endpointFor(execution: ToolExecution): string | null {
  if (execution.tool_type === 'mcp') return execution.mcp_server_url ?? null;
  return execution.tool_url ?? null;
}

/** Auth label for the row — webhook auth_type for custom/built-in tools,
 *  the MCP transport for MCP tools, `null` otherwise. */
export function authFor(execution: ToolExecution): string | null {
  if (execution.tool_type === 'mcp') return execution.mcp_server_transport ?? null;
  return execution.tool_auth_type ?? null;
}

/** Format an ISO timestamp as `HH:MM:SS` (UTC fallback) — null-safe. */
export function formatStartedAt(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString();
}

/** Aggregate counts/avg for the summary tiles above the table.
 *
 *  `total` is the count of *all* LLM-proposed tool calls (every row). `executed`
 *  is the subset that actually ran (`success` + `error`). `notExecuted` is
 *  `proposed` + `cancelled` — LLM asked but the handler never returned. This
 *  split matches the four lifecycle statuses `ToolExecution.status` can take. */
export interface ToolExecutionSummary {
  total: number;
  executed: number;
  notExecuted: number;
  success: number;
  errors: number;
  proposed: number;
  cancelled: number;
  avgDurationMs: number | null;
}

export function summarize(rows: ToolExecution[]): ToolExecutionSummary {
  const total = rows.length;
  let success = 0;
  let errors = 0;
  let proposed = 0;
  let cancelled = 0;
  let durationSum = 0;
  let durationCount = 0;

  for (const row of rows) {
    switch (row.status) {
      case 'success':
        success += 1;
        break;
      case 'error':
        errors += 1;
        break;
      case 'proposed':
        proposed += 1;
        break;
      case 'cancelled':
        cancelled += 1;
        break;
      default:
        break;
    }
    if (typeof row.duration_ms === 'number') {
      durationSum += row.duration_ms;
      durationCount += 1;
    }
  }

  return {
    total,
    executed: success + errors,
    notExecuted: proposed + cancelled,
    success,
    errors,
    proposed,
    cancelled,
    avgDurationMs: durationCount > 0 ? Math.round(durationSum / durationCount) : null,
  };
}

/** Stable JSON formatter for the detail drawer. Falls back to `String()`. */
export function prettyJson(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export const STATUS_FILTER_OPTIONS: ReadonlyArray<{
  key: 'all' | ToolExecutionStatus;
  label: string;
}> = [
  { key: 'all', label: 'All statuses' },
  { key: 'success', label: 'Success only' },
  { key: 'error', label: 'Errors only' },
  { key: 'proposed', label: 'Proposed only' },
  { key: 'cancelled', label: 'Cancelled only' },
];
