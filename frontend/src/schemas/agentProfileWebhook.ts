import { z } from 'zod';

/**
 * Client-side validation for the webhook config form. Mirrors the backend rules
 * in `core/services/agents/agent_profile_webhook_service.py` (https-only,
 * method, identifiers, timeout clamp) — UX-only; the server re-enforces them.
 */
export const webhookConfigSchema = z.object({
  endpoint_url: z
    .string()
    .trim()
    .min(1, 'Endpoint URL is required.')
    .max(500, 'URL is too long (max 500 characters).')
    .url('Enter a valid URL.')
    .refine((u) => u.startsWith('https://'), 'URL must start with https://'),
  http_method: z.enum(['GET', 'POST']),
  // RHF field-array shape (RHF supplies each row's key via its own `id`);
  // serialized to a key→value map on submit.
  headers: z.array(z.object({ key: z.string(), value: z.string() })),
  request_identifiers: z.array(
    z.object({
      identifier: z.literal('phone'),
      param: z.string().trim().min(1, 'Param name is required.').max(120),
      in: z.enum(['query', 'body']),
    }),
  ),
  directions: z
    .object({ inbound: z.boolean(), outbound: z.boolean() })
    .refine((d) => d.inbound || d.outbound, 'Enable at least one direction.'),
  timeout_seconds: z.coerce
    .number()
    .int('Timeout must be a whole number of seconds.')
    .min(1, 'Minimum is 1 second.')
    .max(30, 'Maximum is 30 seconds.'),
  is_enabled: z.boolean(),
});

export type WebhookConfigFormValues = z.infer<typeof webhookConfigSchema>;
