import { CheckCircle2, Clock, Loader2, MinusCircle, XCircle } from 'lucide-react';
import type { ReactNode } from 'react';

import type {
  AgentLlmEvalBatchStatus,
  AgentLlmEvalScenarioSource,
  AgentLlmEvalVerdict,
} from '@/types/agentLlmEval';

// ── Shared verdict chip styles ──────────────────────────────────────────

export const VERDICT_STYLES: Record<
  AgentLlmEvalVerdict,
  { label: string; className: string; icon: ReactNode }
> = {
  PASS: {
    label: 'Pass',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  PARTIAL: {
    label: 'Partial',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <MinusCircle className="size-3" />,
  },
  FAIL: {
    label: 'Fail',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

// ── Run status chip styles ──────────────────────────────────────────────

// Chip for the Runs tab's status column. Same visual grammar as
// ``VerdictChip`` so the two feel like siblings. Terminal states are
// definitive (Completed / Failed); non-terminal states use motion cues
// (spinner for running, clock for pending) so the eye picks them out
// without a colour scan.
export const RUN_STATUS_STYLES: Record<
  AgentLlmEvalBatchStatus,
  { label: string; className: string; icon: ReactNode }
> = {
  pending: {
    label: 'Pending',
    className: 'bg-muted text-muted-foreground ring-1 ring-border',
    icon: <Clock className="size-3" />,
  },
  running: {
    label: 'Running',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <Loader2 className="size-3 animate-spin" />,
  },
  completed: {
    label: 'Completed',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  failed: {
    label: 'Failed',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

// Terminal states = drawer is safe to open (results are persisted).
// Non-terminal rows (pending / running) suppress the drawer and show a
// muted "Scoring N of M" progress readout in the Result column instead.
export const RUN_TERMINAL_STATUSES: ReadonlySet<AgentLlmEvalBatchStatus> = new Set([
  'completed',
  'failed',
]);

// ── Sample CSV template ─────────────────────────────────────────────────
//
// The CSV importer on the backend accepts these column headers (see
// ``_CSV_ALLOWED_COLUMNS`` in ``core/services/evals/agent_llm/scenario_service.py``).
// ``scenario_key`` and ``prompt`` are required; the rest are optional.
// Kept inline in this file — the LLM Evals import flow is the only caller,
// and the header list needs to stay in lock-step with the backend allow-list.
export const SAMPLE_CSV_HEADERS = [
  'scenario_key',
  'prompt',
  'expected_answer',
  'persona_criteria',
  'instruction_criteria',
  'tags',
  'folder',
] as const;

export const SAMPLE_CSV_ROWS: readonly (readonly string[])[] = [
  [
    'happy_path_booking',
    'I would like to book a deluxe room for two from June 10th to June 12th.',
    'Confirms availability and reads back the dates and room type.',
    'Warm, professional, concise',
    'Do not invent a price; confirm the reservation before ending the call.',
    'booking,happy_path',
    'Booking',
  ],
  [
    'refund_request',
    'I want a refund for my last stay because the room was not clean.',
    'Acknowledges the issue, apologizes, and offers a refund per policy.',
    'Empathetic, calm',
    'Never blame the guest; always offer a resolution.',
    'refund,complaint',
    'Support',
  ],
  [
    'out_of_scope',
    "Can you tell me tomorrow's weather forecast?",
    'Politely declines and redirects to hotel-related topics.',
    'Polite, brief',
    'Do not answer questions unrelated to the hotel.',
    'guardrail',
    '',
  ],
];

// Sentinel option value used by ``FolderPicker``'s inline SelectInput to
// represent the "Create new folder…" affordance. Any string not otherwise
// a folder id is fine; using a reserved token avoids clashing with a
// real UUID.
export const NEW_FOLDER_OPTION_VALUE = '__new_folder__';

// ── Scenarios source filter ─────────────────────────────────────────────

export const SCENARIO_SOURCE_OPTIONS: {
  value: AgentLlmEvalScenarioSource;
  label: string;
}[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'csv', label: 'CSV import' },
  { value: 'generated', label: 'Auto-generated' },
  { value: 'fixture', label: 'Fixture' },
];

// Sentinel for the "no source filter" option. Radix Select forbids an
// empty-string value on ``<Select.Item>`` (it's reserved for clearing
// the selection to the placeholder), so we use a non-empty token and
// map it back to ``null`` at the callback boundary.
export const SOURCE_FILTER_ALL_VALUE = '__all__';

// ── Pagination footer ───────────────────────────────────────────────────

export const LLM_EVALS_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

// ── Generate scenarios modal ────────────────────────────────────────────

// Bound + default match the backend's ``_MAX_COUNT`` in
// ``scenario_generation/strategies/llm.py`` — the server clamps anyway, but
// mirroring the bound here saves a round-trip on a mistyped input.
export const GENERATE_DEFAULT_COUNT = 10;
export const GENERATE_MAX_COUNT = 50;
