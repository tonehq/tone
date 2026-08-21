import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { evalSettingsApi, type EvalSettingsPatch } from '@/services/evalSettingsService';

export const EVAL_SETTINGS_QUERY_KEY = 'eval-settings';
export const EVAL_MODEL_OPTIONS_QUERY_KEY = 'eval-model-options';

// Model catalog for the generation / answer dropdowns. Rarely changes (only
// when an admin adds a new model in Services → OpenAI / Google), so we cache
// aggressively — the settings page will pick up new models on next mount.
export function useEvalModelOptions() {
  return useQuery({
    queryKey: [EVAL_MODEL_OPTIONS_QUERY_KEY],
    queryFn: () => evalSettingsApi.listModelOptions(),
    staleTime: 5 * 60_000,
  });
}

export function useEvalSettings() {
  return useQuery({
    queryKey: [EVAL_SETTINGS_QUERY_KEY],
    queryFn: () => evalSettingsApi.get(),
    // Eval settings are rarely edited; a stale window avoids the double-fetch
    // pattern (mount → refocus) when a user is just browsing the form.
    staleTime: 60_000,
  });
}

export function useUpdateEvalSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: EvalSettingsPatch) => evalSettingsApi.update(patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [EVAL_SETTINGS_QUERY_KEY] });
    },
  });
}
