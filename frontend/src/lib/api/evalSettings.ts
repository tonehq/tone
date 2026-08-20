import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { evalSettingsApi, type EvalSettingsPatch } from '@/services/evalSettingsService';

export const EVAL_SETTINGS_QUERY_KEY = 'eval-settings';

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
