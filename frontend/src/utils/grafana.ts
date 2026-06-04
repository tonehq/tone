import { GRAFANA_BASE_URL, GRAFANA_LOG_APP } from '@/constants';

/** Padding added around a call's time range so the Loki window comfortably brackets it. */
const TIME_BUFFER_MS = 5 * 60 * 1000;

/**
 * Pre-encoded Grafana Loki Explore URL, filtered to a single trace_id.
 *
 * Placeholders ({BASE}, {APP}, {FROM}, {TO}, {TRACE_ID}) are substituted by
 * buildGrafanaLogsUrl. The query string is already URL-encoded (%7C%3D%7C === "|=|", and
 * __gfc__ is Grafana's in-value comma escape); trace_id and app values are URL-safe, so
 * plain string substitution is correct here — do not re-encode.
 */
const GRAFANA_LOGS_URL_TEMPLATE =
  '{BASE}/a/grafana-lokiexplore-app/explore/app/{APP}/logs' +
  '?from={FROM}&to={TO}&var-ds=grafanacloud-logs&var-filters=app%7C%3D%7C{APP}' +
  '&patterns=%5B%5D&var-lineFormat=' +
  '&var-fields=trace_id%7C%3D%7C%7B%22parser%22:%22logfmt%22__gfc__%22value%22:%22{TRACE_ID}%22%7D,{TRACE_ID}' +
  '&var-levels=&var-metadata=&var-jsonFields=&var-patterns=&var-lineFilterV2=&var-lineFilters=&timezone=browser' +
  '&var-all-fields=trace_id%7C%3D%7C%7B%22parser%22:%22logfmt%22__gfc__%22value%22:%22{TRACE_ID}%22%7D,{TRACE_ID}' +
  '&var-levels=&var-metadata=&var-jsonFields=&var-patterns=&var-lineFilterV2=&var-lineFilters=&timezone=browser' +
  '&userDisplayedFields=false&displayedFields=%5B%5D' +
  '&urlColumns=%5B%22Time%22,%22Line%22,%22detected_level%22%5D' +
  '&visualizationType=%22table%22&sortOrder=%22Descending%22';

interface GrafanaLogsCall {
  trace_id: string | null;
  started_at: string | null;
  ended_at: string | null;
}

/**
 * Build a Grafana Loki Explore URL filtered to this call's trace_id. The time window is
 * derived from the call's start/end (padded by TIME_BUFFER_MS) so the logs load regardless
 * of the call's age. Returns null when the call has no trace_id (e.g. legacy rows).
 */
export function buildGrafanaLogsUrl(call: GrafanaLogsCall): string | null {
  const traceId = call.trace_id;
  if (!traceId) return null;

  const startMs = call.started_at ? Date.parse(call.started_at) : NaN;
  const endMs = call.ended_at ? Date.parse(call.ended_at) : NaN;
  const from = (Number.isNaN(startMs) ? Date.now() : startMs) - TIME_BUFFER_MS;
  const to = (Number.isNaN(endMs) ? Date.now() : endMs) + TIME_BUFFER_MS;

  return GRAFANA_LOGS_URL_TEMPLATE.replaceAll('{BASE}', GRAFANA_BASE_URL)
    .replaceAll('{APP}', GRAFANA_LOG_APP)
    .replaceAll('{FROM}', String(from))
    .replaceAll('{TO}', String(to))
    .replaceAll('{TRACE_ID}', traceId);
}
