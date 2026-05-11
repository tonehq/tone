import { z } from 'zod';

export const providerUpsertSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  display_name: z.string().min(1, 'Display name is required'),
  description: z.string().optional(),
  base_url: z.string().optional(),
});

export type ProviderUpsertFormData = z.infer<typeof providerUpsertSchema>;

export const apiKeyUpsertSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  api_key: z.string().optional(),
  description: z.string().optional(),
});

export type ApiKeyUpsertFormData = z.infer<typeof apiKeyUpsertSchema>;

export const apiKeyCreateSchema = apiKeyUpsertSchema.extend({
  api_key: z.string().min(1, 'API key is required'),
});

export type ApiKeyCreateFormData = z.infer<typeof apiKeyCreateSchema>;

export const modelUpsertSchema = z.object({
  name: z.string().min(1, 'Model name is required'),
});

export type ModelUpsertFormData = z.infer<typeof modelUpsertSchema>;

export const serviceUpsertSchema = z.object({
  name: z.string().min(1, 'Service name is required'),
  description: z.string().optional(),
});

export type ServiceUpsertFormData = z.infer<typeof serviceUpsertSchema>;
