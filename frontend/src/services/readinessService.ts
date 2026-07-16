import axiosInstance from '@/utils/axios';
import type {
  ReadinessDepth,
  ReadinessReport,
  ReadinessSummary,
  ReadinessTrigger,
} from '@/types/readiness';

/** Body of POST /agent/{id}/readiness. Optional fields are omitted when
 * unset so backend defaults apply. */
interface ReadinessRequestBody {
  depth: ReadinessDepth;
  config_id?: string;
  trigger?: string;
}

/**
 * Run a readiness check for one agent + (optionally explicit) config.
 * - Depth `shallow`: DB-only, safe on hot paths.
 * - Depth `deep`: hits real providers; rate-limited to 1/min per agent server-side.
 *
 * Errors bubble up unmodified so the caller can inspect status + payload
 * (needed by the publish flow to distinguish `readiness_blocked` vs
 * `readiness_warnings`). Non-publish callers should wrap in `handleApiError`.
 */
export const getAgentReadiness = async (
  agentId: string,
  depth: ReadinessDepth,
  configId?: string,
  trigger?: ReadinessTrigger | string,
): Promise<ReadinessReport> => {
  const body: ReadinessRequestBody = { depth };
  if (configId) body.config_id = configId;
  if (trigger) body.trigger = trigger;
  const res = await axiosInstance.post<ReadinessReport>(`/agent/${agentId}/readiness`, body);
  return res.data;
};

/**
 * Cheap summary shape for the agent list badge. Always Shallow — the badge
 * doesn't need per-check detail. Trigger defaults to `list_page` if omitted
 * so backend analytics can distinguish list impressions from editor loads.
 */
export const getAgentReadinessSummary = async (
  agentId: string,
  configId?: string,
  trigger: ReadinessTrigger | string = 'list_page',
): Promise<ReadinessSummary> => {
  const res = await axiosInstance.get<ReadinessSummary>(`/agent/${agentId}/readiness/summary`, {
    params: { ...(configId ? { config_id: configId } : {}), trigger },
  });
  return res.data;
};
