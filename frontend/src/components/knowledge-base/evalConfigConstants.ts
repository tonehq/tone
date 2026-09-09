// Static config for the Evaluation Config tab. Metric + engine option sets are
// reused from the eval-settings types so the config editor offers the same
// choices as Settings → Evaluations (single source of truth).

import { EVAL_JUDGE_ENGINES, EVAL_METRIC_NAMES } from '@/types/evalSettings';

export { EVAL_JUDGE_ENGINES, EVAL_METRIC_NAMES };

// The GEval metric that carries a config's custom rubric prompt. Kept in sync
// with the backend ``EvaluationConfigService._CUSTOM_PROMPT_METRIC``.
export const CUSTOM_PROMPT_METRIC = 'correctness';

export const DEFAULT_METRIC_THRESHOLD = 0.7;

// Up to this many config passes can be compared side by side.
export const MAX_COMPARE = 3;

export interface EvalConfigFormState {
  name: string;
  description: string;
  judge_model: string;
  judge_engine: string;
  judge_prompt: string;
  metrics_enabled: string[];
  metric_threshold: string;
  is_default: boolean;
}

export const EMPTY_CONFIG_FORM: EvalConfigFormState = {
  name: '',
  description: '',
  judge_model: '',
  judge_engine: 'deepeval',
  judge_prompt: '',
  metrics_enabled: ['faithfulness', 'answer_relevancy', 'correctness'],
  metric_threshold: String(DEFAULT_METRIC_THRESHOLD),
  is_default: false,
};
