import type {
  EvalModelCatalog,
  EvalSettings,
  LlmEvalOrgSettings,
  RagEvalOrgSettings,
} from '@/types/evalSettings';
import axios from '@/utils/axios';

// Backend routes: core/api/v1/organizations.py — GET/PUT /organization/eval-settings
// GET returns the raw JSONB — the two sub-objects ``rag_evals`` and
// ``llm_evals``. Missing keys stay absent (do NOT default them client-side;
// unset means "resolved from env / hardcoded default at eval time").
// PUT accepts a partial patch shaped like the storage — each slot may be
// present with a subset of keys OR set to ``null`` to drop the whole slot;
// inside a slot, a field set to ``null`` is DELETED from the stored JSONB
// so the resolver falls back to env / hardcoded default. That's how the UI
// expresses "revert this field to fallback" when the user clears an input.

type SlotPatch<T> = { [K in keyof T]?: T[K] | null };
export type RagEvalPatch = SlotPatch<RagEvalOrgSettings>;
export type LlmEvalPatch = SlotPatch<LlmEvalOrgSettings>;

export interface EvalSettingsPatch {
  rag_evals?: RagEvalPatch | null;
  llm_evals?: LlmEvalPatch | null;
}

export const evalSettingsApi = {
  get: async (): Promise<EvalSettings> => {
    const { data } = await axios.get<EvalSettings>('/organization/eval-settings');
    return data ?? {};
  },
  update: async (
    patch: EvalSettingsPatch,
  ): Promise<{ message: string; eval_settings: EvalSettings }> => {
    const { data } = await axios.put<{ message: string; eval_settings: EvalSettings }>(
      '/organization/eval-settings',
      patch,
    );
    return data;
  },
  // Read-only catalog of OpenAI + Gemini LLM models available as generation
  // / answer model choices on the Evaluations settings page. Backed by
  // ``EvalModelsService.list_llm_options`` (org-member auth).
  listModelOptions: async (): Promise<EvalModelCatalog> => {
    const { data } = await axios.get<EvalModelCatalog>('/organization/eval-settings/models');
    return data ?? { providers: [], models: [] };
  },
};
