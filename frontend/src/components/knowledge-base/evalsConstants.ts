import type { EvalVersion } from '@/types/eval';

// The in-progress form shape for adding / editing an eval question. Kept out of
// the components (repo rule: no inlined constants/types in a component) so both
// the add form (ManageEvalsTab) and the inline edit (EvalQuestionRow) share it.
export interface DraftQuestion {
  question: string;
  expected_answer: string;
  expected_source_snippet: string;
  category: string;
}

export const EMPTY_DRAFT: DraftQuestion = {
  question: '',
  expected_answer: '',
  expected_source_snippet: '',
  category: '',
};

// Human label for a version in a picker, e.g. "v3 · draft · 12 approved".
export function versionLabel(v: EvalVersion): string {
  const status =
    v.status === 'generating' ? 'generating…' : v.status === 'finalized' ? 'finalized' : 'draft';
  return `v${v.version_number} · ${status} · ${v.counts.approved}/${v.counts.total} approved`;
}
