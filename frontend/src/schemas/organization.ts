import { z } from 'zod';

export const organizationUpsertSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  website_url: z.string().optional(),
  logo_url: z.string().optional(),
});

export type OrganizationUpsertFormData = z.infer<typeof organizationUpsertSchema>;

export const organizationDeleteSchema = z.object({
  confirm_name: z.string().min(1, 'Please type the organization name'),
});

export type OrganizationDeleteFormData = z.infer<typeof organizationDeleteSchema>;
