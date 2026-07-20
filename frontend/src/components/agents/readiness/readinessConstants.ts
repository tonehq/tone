/**
 * Presentation constants for readiness UI. Kept in one file so category
 * labels, order, and severity/status colour maps stay DRY across every
 * consumer (drawer, badge, check row, confirm dialog).
 */

import type { ReadinessCategory, ReadinessSeverity } from '@/types/readiness';

/** Human-readable label for each category. Used as group headings in the drawer. */
export const CATEGORY_LABEL: Record<ReadinessCategory, string> = {
  llm: 'LLM',
  stt: 'Speech-to-text',
  tts: 'Voice',
  phone: 'Phone',
  tools: 'Tools',
  knowledge_bases: 'Knowledge bases',
  mcp_servers: 'MCP servers',
};

/**
 * The order in which categories appear in the drawer. Mirrors the natural
 * order of the pipeline: brain (LLM) → ears (STT) → mouth (TTS) → routing
 * (Phone) → attached extras (Tools, Knowledge bases, MCP).
 */
export const CATEGORY_ORDER: ReadinessCategory[] = [
  'llm',
  'stt',
  'tts',
  'phone',
  'tools',
  'knowledge_bases',
  'mcp_servers',
];

/**
 * Severity rank — descending. Used to sort failed checks within a category
 * so the eye lands on blockers first.
 */
export const SEVERITY_RANK: Record<ReadinessSeverity, number> = {
  blocker: 0,
  warning: 1,
  info: 2,
};

/** Colour tokens matching ReadinessBadge, applied to icons + text inside rows. */
export const SEVERITY_TEXT_CLASS: Record<ReadinessSeverity, string> = {
  blocker: 'text-destructive',
  warning: 'text-amber-600 dark:text-amber-400',
  info: 'text-muted-foreground',
};

/** Sentinel value for the "Latest run" option in the run-history select. */
export const RUN_HISTORY_LATEST_VALUE = 'latest';
