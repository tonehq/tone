import { z } from 'zod';

export const builtInToolSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().min(1, 'Description is required').max(1000, 'Description is too long'),
});

export type BuiltInToolFormData = z.infer<typeof builtInToolSchema>;

export const customToolSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().min(1, 'Description is required'),
  url: z.string().min(1, 'URL is required').url('Please enter a valid URL'),
});

export type CustomToolFormData = z.infer<typeof customToolSchema>;
