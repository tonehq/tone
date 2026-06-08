import type { CallFilterState, FacetSectionConfig } from '@/types/callHistoryFilters';

// Avg-latency slider bounds — shared with the page so "active" detection and
// the reset baseline stay in one place.
export const MIN_LATENCY_SECONDS = 0;
export const MAX_LATENCY_SECONDS = 5;
export const LATENCY_STEP = 0.1;
export const DEFAULT_LATENCY_RANGE: [number, number] = [MIN_LATENCY_SECONDS, MAX_LATENCY_SECONDS];

/** Every faceted (checkbox) field, in display order. Used by the token search. */
export const FACET_SECTIONS: FacetSectionConfig[] = [
  { field: 'status', label: 'Status', titleCase: true },
  { field: 'agent_name', label: 'Agent' },
  { field: 'direction', label: 'Direction', titleCase: true },
  { field: 'channel_type', label: 'Channel', titleCase: true },
  { field: 'llm_model', label: 'LLM Model' },
  { field: 'stt_model', label: 'STT Model' },
  { field: 'tts_model', label: 'TTS Model' },
];

// All facets (including Status and Agent) live inside the drawer; the toolbar
// only keeps the token search + Columns + Filters.
export const DRAWER_FACET_SECTIONS = FACET_SECTIONS;
export const DRAWER_FIELD_KEYS = new Set(DRAWER_FACET_SECTIONS.map((s) => s.field));

export const titleCase = (v: string) =>
  v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export const isLatencyActive = (r: [number, number]) =>
  r[0] > MIN_LATENCY_SECONDS || r[1] < MAX_LATENCY_SECONDS;

export const createEmptyFilterState = (timeZone: string): CallFilterState => ({
  dateRange: { start: null, end: null, timeZone },
  facets: {},
  minTurns: '',
  maxTurns: '',
  latency: DEFAULT_LATENCY_RANGE,
});

/** Active filters managed inside the drawer (date + all facets + turns + latency). */
export function countDrawerFilters(state: CallFilterState): number {
  const facetCount = DRAWER_FACET_SECTIONS.reduce(
    (n, s) => n + ((state.facets[s.field]?.length ?? 0) > 0 ? 1 : 0),
    0,
  );
  const turnsActive = state.minTurns.trim() !== '' || state.maxTurns.trim() !== '';
  const dateActive = !!(state.dateRange.start && state.dateRange.end);
  return (
    facetCount +
    (turnsActive ? 1 : 0) +
    (isLatencyActive(state.latency) ? 1 : 0) +
    (dateActive ? 1 : 0)
  );
}
