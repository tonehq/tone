import { DEFAULT_WEBHOOK_TIMEOUT_SECONDS } from '@/constants/profileWebhook';
import type { WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';
import type {
  AgentProfileWebhook,
  ProfileWebhookUpsertInput,
  RequestIdentifier,
} from '@/types/agentProfileWebhook';

export function headersMapToFormRows(
  map: Record<string, string>,
): { key: string; value: string }[] {
  return Object.entries(map || {}).map(([key, value]) => ({ key, value }));
}

/** Array → map, dropping blank-key rows (mirrors the MCP form's serializer). */
export function headerRowsToMap(rows: { key: string; value: string }[]): Record<string, string> {
  return Object.fromEntries(rows.filter((h) => h.key.trim()).map((h) => [h.key.trim(), h.value]));
}

const DEFAULT_IDENTIFIER: RequestIdentifier = { identifier: 'phone', param: 'phone', in: 'query' };

export function emptyWebhookForm(): WebhookConfigFormValues {
  return {
    endpoint_url: '',
    http_method: 'POST',
    headers: [],
    request_identifiers: [{ ...DEFAULT_IDENTIFIER }],
    directions: { inbound: true, outbound: false },
    timeout_seconds: DEFAULT_WEBHOOK_TIMEOUT_SECONDS,
    is_enabled: false,
  };
}

export function webhookToFormValues(config: AgentProfileWebhook | null): WebhookConfigFormValues {
  if (!config) return emptyWebhookForm();
  return {
    endpoint_url: config.endpoint_url,
    http_method: config.http_method,
    headers: headersMapToFormRows(config.headers || {}),
    request_identifiers: config.request_identifiers?.length
      ? config.request_identifiers.map((r) => ({
          identifier: 'phone' as const,
          param: r.param,
          in: r.in,
        }))
      : [{ ...DEFAULT_IDENTIFIER }],
    directions: {
      inbound: !!config.directions?.inbound,
      outbound: !!config.directions?.outbound,
    },
    timeout_seconds: config.timeout_seconds || DEFAULT_WEBHOOK_TIMEOUT_SECONDS,
    is_enabled: config.is_enabled,
  };
}

export function formValuesToUpsertInput(
  values: WebhookConfigFormValues,
): ProfileWebhookUpsertInput {
  return {
    endpoint_url: values.endpoint_url.trim(),
    http_method: values.http_method,
    headers: headerRowsToMap(values.headers),
    request_identifiers: values.request_identifiers.map((r) => ({
      identifier: 'phone' as const,
      param: r.param.trim(),
      in: r.in,
    })),
    directions: values.directions,
    timeout_seconds: values.timeout_seconds,
    is_enabled: values.is_enabled,
  };
}
